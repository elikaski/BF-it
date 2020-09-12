#include <exception>
#include <vector>
#include <list>
#include <unordered_map>
#include <unordered_set>

using namespace std;

// if size of pointer will ever be too small change here
typedef unsigned int pointer_t;

class UnbalancedBracket : public exception {
    virtual const char* what() const throw() {
        return "Unbalanced square brackets caugt";
    }
};

class TapeLeftBound : public exception {
    virtual const char* what() const throw() {
        return "Tape pointer tried leaving tape";
    }
};


// possible commands enumeration
enum Command : unsigned char {
    inc,
    dec,
    left,
    right,
    in,
    out,
    open,
    close,
};

class Interpreter {
private:
    const string bf_path;
    bool debug_mode;
    vector<Command> commands;
    list<unsigned char> tape;
    // using two mappings will allow faster lookup since type of jump is known
    unordered_map<pointer_t, pointer_t> forward_jumps;
    unordered_map<pointer_t, pointer_t> backward_jumps;
    unordered_set<pointer_t> breakpoints;
    pointer_t command_pointer;
    list<unsigned char>::iterator tape_iterator;
    

    void input();
    void output() const;
    bool step();
public:
    Interpreter(const string& bf_path);
    Interpreter& execute(unsigned int count);
    Interpreter& run();
    Interpreter& new_br(pointer_t at);
    Interpreter& remove_br(pointer_t at);
    bool is_finished() const;
    void set_debug_mode(bool mode);
};