#include <bits/stdc++.h>
using namespace std;

/*
 BGL format example:
 "-" 2006-03-02-00.17.11.137476  "node" "R08-M0-N4-C:J44-U11" memLog [6874.691561] L4 FetchError on ... 
 First token = alert marker
*/

struct Template {
    vector<string> tokens;
};

string normalize_token(const string &tok) {
    // Числа и hex → wildcard
    bool num = true, hex = true;
    for (char c : tok) {
        if (!isdigit(c)) num = false;
        if (!isxdigit(c)) hex = false;
    }
    if (num || hex) return "<*>";

    if (tok.size() > 0 && (tok[0] == '"' || tok.back() == '"')) return "<*>";

    return tok;
}

vector<string> split(const string &s) {
    vector<string> out;
    string tmp;
    stringstream ss(s);
    while (ss >> tmp) out.push_back(tmp);
    return out;
}

string join(const vector<string> &v) {
    string s;
    for (size_t i=0;i<v.size();i++){
        s += v[i];
        if (i + 1 < v.size()) s += " ";
    }
    return s;
}

int main(int argc, char **argv) {
    if (argc < 4) {
        cerr << "Usage: <bgl.log> <encoding> <out_dir>\n";
        return 1;
    }
    string path = argv[1];
    string outdir = argv[3];

    system((string("mkdir -p ") + outdir).c_str());

    // ================= PASS 1: build templates & DF =================

    unordered_map<string,int> template_id;      // template_string -> id
    vector<Template> templates;                 // id -> template vector
    unordered_map<int,int> docfreq;             // template_id -> df count
    long long num_docs = 0;

    {
        ifstream fin(path);
        if (!fin.is_open()) {
            cerr << "Failed to open input log\n";
            return 2;
        }
        string line;
        while (getline(fin, line)) {
            if (line.empty()) continue;
            num_docs++;

            // extract tokens
            auto toks = split(line);
            if (toks.empty()) continue;

            // remove alert token
            string alert = toks[0];
            vector<string> msg(toks.begin() + 1, toks.end());

            // normalize tokens → template signature
            vector<string> norm;
            for (auto &t : msg) norm.push_back(normalize_token(t));

            string tpl = join(norm);

            int id;
            auto it = template_id.find(tpl);
            if (it == template_id.end()) {
                id = templates.size();
                template_id[tpl] = id;
                templates.push_back({norm});
            } else {
                id = it->second;
            }
            docfreq[id]++;
        }
    }

    int dim = templates.size();

    // compute IDF
    vector<double> idf(dim,0.0);
    for (int i=0;i<dim;i++){
        double df = (docfreq.count(i) ? docfreq[i] : 1);
        idf[i] = log((double)num_docs / df);
    }

    // save templates.json
    {
        ofstream jt(outdir + "/templates.json");
        jt << "[\n";
        for (size_t i=0;i<templates.size();i++){
            jt << "  {\"id\": " << i << ", \"tokens\": [";
            for (size_t j=0;j<templates[i].tokens.size();j++){
                jt << "\"" << templates[i].tokens[j] << "\"";
                if (j + 1 < templates[i].tokens.size()) jt << ",";
            }
            jt << "]}";
            if (i + 1 < templates.size()) jt << ",";
            jt << "\n";
        }
        jt << "]\n";
    }

    // save meta.json
    {
        ofstream jm(outdir + "/meta.json");
        jm << "{\n";
        jm << "  \"num_docs\": " << num_docs << ",\n";
        jm << "  \"vocab_size\": " << dim << ",\n";
        jm << "  \"templates\": " << dim << "\n";
        jm << "}\n";
    }

    // ================= PASS 2: write vectors.jsonl =================
    {
        ifstream fin(path);
        ofstream jout(outdir + "/vectors.jsonl");

        string line;
        long long line_id = 0;
        while (getline(fin, line)) {
            if (line.empty()) continue;
            auto toks = split(line);
            if (toks.empty()) continue;

            string alert = toks[0];
            bool is_alert = (alert != "-");
            vector<string> msg(toks.begin() + 1, toks.end());

            // normalize
            vector<string> norm;
            for (auto &t : msg) norm.push_back(normalize_token(t));
            string tpl = join(norm);

            auto it = template_id.find(tpl);
            int tid = (it == template_id.end() ? -1 : it->second);

            // build vector: only 1 nonzero = tf*idf = 1*idf
            vector<int> indices;
            vector<double> vals;

            if (tid >= 0) {
                indices.push_back(tid);
                vals.push_back(idf[tid]);
            }

            // output JSONL
            jout << "{";
            jout << "\"line_id\":" << line_id << ",";
            jout << "\"alert_tag\":\"" << alert << "\",";
            jout << "\"is_alert\":" << (is_alert?"true":"false") << ",";
            jout << "\"template_id\":" << tid << ",";
            jout << "\"dim\":" << dim << ",";
            jout << "\"indices\":[";
            for (size_t i=0;i<indices.size();i++){
                jout << indices[i];
                if (i + 1 < indices.size()) jout << ",";
            }
            jout << "],\"values\":[";
            for (size_t i=0;i<vals.size();i++){
                jout << vals[i];
                if (i + 1 < vals.size()) jout << ",";
            }
            jout << "]}";
            jout << "\n";

            line_id++;
        }
    }

    cerr << "[OK] templates=" << templates.size() << " docs=" << num_docs << "\n";
    return 0;
}

