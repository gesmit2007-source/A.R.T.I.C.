// A.R.T.I.C. core: fast vault indexer (BM25 + wikilink graph), exposed via a C ABI.
#include <algorithm>
#include <cctype>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <sstream>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

#if defined(_WIN32)
#define ARTIC_API __declspec(dllexport)
#else
#define ARTIC_API
#endif

namespace fs = std::filesystem;

namespace {

struct Doc {
    std::string path, title, excerpt;
    std::vector<std::string> links, tags;
    std::unordered_map<std::string, int> tf;
    int len = 0;
};

struct Index {
    std::string root;
    std::vector<Doc> docs;
    std::unordered_map<std::string, int> df;
    std::unordered_map<std::string, int> by_title;
    double total_len = 0;
    double avglen = 1;
};

const std::unordered_set<std::string> kStop = {
    "the","and","for","are","but","not","you","all","can","was","with","that","this",
    "have","from","they","will","what","when","your","about","into","than","then","them"};

std::string lower(std::string s) {
    for (auto& c : s) c = (char)std::tolower((unsigned char)c);
    return s;
}

std::vector<std::string> tokenize(const std::string& s) {
    std::vector<std::string> out;
    std::string cur;
    auto flush = [&] {
        if (cur.size() >= 2 && !kStop.count(cur)) out.push_back(cur);
        cur.clear();
    };
    for (unsigned char c : s) {
        if (std::isalnum(c) || c > 127) cur.push_back((char)std::tolower(c));
        else flush();
    }
    flush();
    return out;
}

std::string jesc(const std::string& s) {
    std::string o;
    for (unsigned char c : s) {
        switch (c) {
            case '"': o += "\\\""; break;
            case '\\': o += "\\\\"; break;
            case '\n': o += "\\n"; break;
            case '\r': o += "\\r"; break;
            case '\t': o += "\\t"; break;
            default:
                if (c < 0x20) { char b[8]; snprintf(b, sizeof b, "\\u%04x", c); o += b; }
                else o.push_back((char)c);
        }
    }
    return o;
}

void parse(const std::string& text, Doc& d) {
    for (size_t i = 0; i + 1 < text.size(); ++i) {
        if (text[i] == '[' && text[i + 1] == '[') {
            size_t j = text.find("]]", i + 2);
            if (j == std::string::npos) break;
            std::string t = text.substr(i + 2, j - i - 2);
            t = t.substr(0, t.find_first_of("|#"));
            if (!t.empty()) d.links.push_back(t);
            i = j + 1;
        } else if (text[i] == '#' && std::isalpha((unsigned char)text[i + 1]) &&
                   (i == 0 || std::isspace((unsigned char)text[i - 1]))) {
            size_t j = i + 1;
            while (j < text.size() && (std::isalnum((unsigned char)text[j]) || text[j]=='_' || text[j]=='-' || text[j]=='/')) ++j;
            d.tags.push_back(lower(text.substr(i + 1, j - i - 1)));
            i = j - 1;
        }
    }
}

bool load_doc(const fs::path& p, Doc& d) {
    std::ifstream f(p, std::ios::binary);
    if (!f) return false;
    std::stringstream ss; ss << f.rdbuf();
    std::string text = ss.str();
    d.path = p.string();
    d.title = p.stem().string();
    d.excerpt = text.substr(0, 700);
    parse(text, d);
    for (auto& t : tokenize(text)) { d.tf[t]++; d.len++; }
    for (auto& t : tokenize(d.title)) { d.tf[t] += 3; d.len += 3; }
    return true;
}

}  // namespace

extern "C" {

ARTIC_API void* artic_index_new(const char* root) {
    auto* ix = new Index();
    ix->root = root;
    return ix;
}

ARTIC_API void artic_index_free(void* h) { delete static_cast<Index*>(h); }

ARTIC_API int artic_index_rebuild(void* h) {
    auto* ix = static_cast<Index*>(h);
    ix->docs.clear(); ix->df.clear(); ix->by_title.clear();
    ix->total_len = 0;
    std::error_code ec;
    for (fs::recursive_directory_iterator it(ix->root, fs::directory_options::skip_permission_denied, ec), end;
         it != end; it.increment(ec)) {
        if (ec) break;
        const auto& p = it->path();
        if (it->is_directory(ec)) {
            auto name = p.filename().string();
            bool hidden = !name.empty() && name[0] == '.';
            bool outside = it.depth() == 0 && name != "Notes" && name != "Reflections";
            if (hidden || outside) it.disable_recursion_pending();
            continue;
        }
        if (!it->is_regular_file(ec) || p.extension() != ".md") continue;
        if (p.parent_path() == fs::path(ix->root)) continue;
        Doc d;
        if (!load_doc(p, d)) continue;
        for (auto& kv : d.tf) ix->df[kv.first]++;
        ix->by_title[lower(d.title)] = (int)ix->docs.size();
        ix->total_len += d.len;
        ix->docs.push_back(std::move(d));
    }
    ix->avglen = ix->docs.empty() ? 1 : ix->total_len / ix->docs.size();
    return (int)ix->docs.size();
}

ARTIC_API int artic_index_add(void* h, const char* path) {
    auto* ix = static_cast<Index*>(h);
    fs::path p(path);
    std::error_code ec;
    auto rel = fs::relative(p, ix->root, ec);
    if (!ec) {
        auto first = rel.begin();
        bool scoped = rel.extension() == ".md" && first != rel.end() &&
                      (*first == "Notes" || *first == "Reflections");
        if (!scoped) return (int)ix->docs.size();
    }
    Doc d;
    if (!load_doc(p, d)) return (int)ix->docs.size();
    for (size_t i = 0; i < ix->docs.size(); ++i) {
        auto& old = ix->docs[i];
        if (old.path != d.path) continue;
        for (auto& kv : old.tf) {
            auto f = ix->df.find(kv.first);
            if (f != ix->df.end() && --f->second == 0) ix->df.erase(f);
        }
        ix->total_len -= old.len;
        if (lower(old.title) != lower(d.title)) {
            auto t = ix->by_title.find(lower(old.title));
            if (t != ix->by_title.end() && t->second == (int)i) ix->by_title.erase(t);
        }
        ix->total_len += d.len;
        ix->by_title[lower(d.title)] = (int)i;
        ix->docs[i] = std::move(d);
        ix->avglen = ix->docs.empty() ? 1 : ix->total_len / ix->docs.size();
        return (int)ix->docs.size();
    }
    for (auto& kv : d.tf) ix->df[kv.first]++;
    ix->by_title[lower(d.title)] = (int)ix->docs.size();
    ix->total_len += d.len;
    ix->docs.push_back(std::move(d));
    ix->avglen = ix->docs.empty() ? 1 : ix->total_len / ix->docs.size();
    return (int)ix->docs.size();
}

ARTIC_API char* artic_search(void* h, const char* query, int k) {
    auto* ix = static_cast<Index*>(h);
    const double k1 = 1.5, b = 0.75;
    const double N = (double)ix->docs.size();
    std::vector<std::pair<double, int>> scored;
    auto qt = tokenize(query);
    for (size_t i = 0; i < ix->docs.size(); ++i) {
        const auto& d = ix->docs[i];
        double s = 0;
        for (auto& t : qt) {
            auto f = d.tf.find(t);
            if (f == d.tf.end()) continue;
            double n = ix->df[t];
            double idf = std::log(1.0 + (N - n + 0.5) / (n + 0.5));
            double tf = f->second;
            s += idf * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * d.len / ix->avglen));
        }
        if (s > 0) scored.push_back({s, (int)i});
    }
    std::sort(scored.begin(), scored.end(), [](auto& a, auto& c) { return a.first > c.first; });
    std::string o = "[";
    for (int i = 0; i < k && i < (int)scored.size(); ++i) {
        const auto& d = ix->docs[scored[i].second];
        if (i) o += ",";
        o += "{\"title\":\"" + jesc(d.title) + "\",\"path\":\"" + jesc(d.path) +
             "\",\"score\":" + std::to_string(scored[i].first) +
             ",\"excerpt\":\"" + jesc(d.excerpt) + "\"}";
    }
    o += "]";
    return strdup(o.c_str());
}

ARTIC_API char* artic_backlinks(void* h, const char* title) {
    auto* ix = static_cast<Index*>(h);
    std::string want = lower(title);
    std::string o = "[";
    bool first = true;
    for (auto& d : ix->docs)
        for (auto& l : d.links)
            if (lower(l) == want) {
                if (!first) o += ",";
                o += "\"" + jesc(d.title) + "\"";
                first = false;
                break;
            }
    o += "]";
    return strdup(o.c_str());
}

ARTIC_API char* artic_stats(void* h) {
    auto* ix = static_cast<Index*>(h);
    std::unordered_set<std::string> linked;
    int links = 0;
    for (auto& d : ix->docs)
        for (auto& l : d.links) { linked.insert(lower(l)); ++links; }
    int orphans = 0;
    for (auto& d : ix->docs)
        if (d.links.empty() && !linked.count(lower(d.title))) ++orphans;
    std::string o = "{\"notes\":" + std::to_string(ix->docs.size()) +
                    ",\"links\":" + std::to_string(links) +
                    ",\"orphans\":" + std::to_string(orphans) + "}";
    return strdup(o.c_str());
}

ARTIC_API void artic_free(char* p) { free(p); }

}  // extern "C"
