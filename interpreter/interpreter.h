#pragma once
#include <exception>
#include <vector>
#include <list>
#include <unordered_map>
#include <unordered_set>
#include "command.h"

class UnbalancedBracket : public std::exception {
    virtual const char* what() const throw() {
        return "Unbalanced square brackets caugt";
    }
};

class Interpreter {
private:
    const std::string bf_path;
    bool debug_mode;
    std::vector<std::pair<Command*, bool>> commands;
    std::list<unsigned char> tape;
    std::vector<std::pair<Command*, bool>>::iterator command_iterator;
    std::list<unsigned char>::iterator tape_iterator;   

    bool step();
public:
    Interpreter(const std::string& bf_path);
    ~Interpreter();
    Interpreter& execute(unsigned int count);
    Interpreter& run();
    Interpreter& new_br(size_t at);
    Interpreter& remove_br(size_t at);
    bool is_finished() const;
    void set_debug_mode(bool mode);
    void input();
    void output() const;
};