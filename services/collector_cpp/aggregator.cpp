#include <iostream>
#include <fstream>
#include <filesystem>
#include <string>
#include <vector>
#include <regex>
#include <algorithm>
#include <cctype>
#include <set>
#include <map>

namespace fs = std::filesystem;

class LogAggregator {
    std::string workingPath;
    std::string destinationPath;
    unsigned int BUF_SIZE;

    template<typename Key, typename Value>
    void save_Map_state(const std::map<Key, Value>& dictionary, const fs::path& filePath) {
        std::ofstream csvFile(filePath, std::ios::trunc);
        if (!csvFile.is_open()) {
            std::cerr << "Err open file for saving " << filePath << std::endl;
            return;
        }
        csvFile << "id,template\n";
        for (const auto& pair : dictionary) {
            csvFile << pair.second << ",";
            std::string t = pair.first;
            bool need_quotes = (t.find(',') != std::string::npos) || (t.find('"') != std::string::npos);
            if (need_quotes) {
                std::string esc;
                esc.reserve(t.size() + 8);
                for (char c : t) esc.push_back(c == '"' ? '\'' : c);
                csvFile << "\"" << esc << "\"\n";
            } else {
                csvFile << t << "\n";
            }
        }
        csvFile.close();
    }

    static std::string text_preprocess(const std::string& text) {
        std::regex id_re("\\S*\\d+\\S*");
        std::string temp = std::regex_replace(text, id_re, "");

        std::string result;
        result.reserve(temp.size());
        for (char c : temp) {
            unsigned char uc = static_cast<unsigned char>(c);
            if (!std::isdigit(uc) && !std::ispunct(uc)) {
                result.push_back(static_cast<char>(std::tolower(uc)));
            } else {
                result.push_back(' ');
            }
        }
        result = std::regex_replace(result, std::regex("\\s+"), " ");
        const std::string whitespace = " \t\n\r\f\v";
        size_t start = result.find_first_not_of(whitespace);
        if (start == std::string::npos) return "";
        size_t end = result.find_last_not_of(whitespace);
        return result.substr(start, end - start + 1);
    }

public:
    LogAggregator(const std::string& workingFolder, const std::string& destinationFolder)
        : workingPath(workingFolder), destinationPath(destinationFolder), BUF_SIZE(10000) {
        if (!fs::exists(destinationPath)) fs::create_directories(destinationPath);
    }

    void collect() {
        fs::path dictFile = fs::path(destinationPath) / "dict_templ.csv";
        unsigned int id = 0;
        std::map<std::string, unsigned int> temp_id;

        for (const auto& entry : fs::directory_iterator(workingPath)) {
            if (entry.is_regular_file() && entry.path().extension() == ".log") {
                std::ifstream ifs(entry.path());
                if (!ifs) {
                    std::cerr << "Read err " << entry.path() << std::endl;
                    continue;
                }
                std::string line;
                std::vector<std::string> buffer;
                buffer.reserve(BUF_SIZE);

                while (std::getline(ifs, line)) {
                    buffer.push_back(line);
                    if (buffer.size() == BUF_SIZE) {
                        std::set<std::string> unic;
                        for (const auto& l : buffer) {
                            std::string p = text_preprocess(l);
                            if (!p.empty()) unic.insert(p);
                        }
                        bool map_upd = false;
                        for (const auto& t : unic) {
                            if (temp_id.find(t) == temp_id.end()) {
                                temp_id[t] = id++;
                                map_upd = true;
                            }
                        }
                        if (map_upd) save_Map_state(temp_id, dictFile);
                        buffer.clear();
                    }
                }
                if (!buffer.empty()) {
                    std::set<std::string> unic;
                    for (const auto& l : buffer) {
                        std::string p = text_preprocess(l);
                        if (!p.empty()) unic.insert(p);
                    }
                    bool map_upd = false;
                    for (const auto& t : unic) {
                        if (temp_id.find(t) == temp_id.end()) {
                            temp_id[t] = id++;
                            map_upd = true;
                        }
                    }
                    if (map_upd) save_Map_state(temp_id, dictFile);
                    buffer.clear();
                }
            }
        }
    }
};

int main(int argc, char* argv[]) {
    if (argc != 3) {
        std::cerr << "Usage: " << argv[0] << " <dir_from> <dir_to>\n";
        return 1;
    }
    std::string workingFolder = argv[1];
    std::string destinationFolder = argv[2];
    LogAggregator Agg(workingFolder, destinationFolder);
    Agg.collect();
    std::cout << "Done!" << std::endl;
    return 0;
}

