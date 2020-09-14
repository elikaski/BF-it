#include <iostream>
#include <string>
#include <cstdio>
#include <algorithm>
#include <fstream>
#include <stack>
#include <csignal>
#include "interpreter.h"


void show_interactive_help() {
    cout << "Brainfuck Interpreter/Debugger\n" <<
        "Commands:\n" << 
        "h/help         -   Show this help message\n" << 
        "q/quit         -   Quits\n" << 
        "debug [0/1]    -   Enable or disable debug mode - enables breakpoints\n" << 
        "run            -   Runs until code completion or breakpoint if debug mode is enabled\n" << 
        "run <num>      -   Runs for specified number of steps or breakpoint if debug mode is enabled\n" << 
        "br <cmd-idx>   -   Create breakpoint at the specified command index\n" << 
        "unbr <cmd-idx> -   Removes breakpoint from the specified command index\n" <<  
        "read           -   Print the content of the tape at the current index" <<
        endl;
}

void interactive_mode() {
    string command;
    Interpreter* bf = nullptr;
    

    cout << "Interactive Mode" << endl;

    while (bf == nullptr) {
        cout << "Input bf code path to begin or q to exit\n>>" << flush;
        getline(cin, command);

        if ((command == "q") || (command == "quit")) {
            return;
        }

        try {
            bf = new Interpreter(command);
        }
        catch (const exception& e) {
            cout << "Exception encountered\n" << e.what() << endl;
        }
    }

    cout << "Code parsed successfully" << endl;
    cout << "Input command or help for list of commands" << endl;

    while ((command != "q") && (command != "quit") && !bf->is_finished()) {
        cout << ">>" << flush;
        getline(cin, command);

        if (command == "") {
            continue;
        }

        // single word commands parsed first
        if ((command == "h") || (command == "help")) {
            show_interactive_help();
        }
        else if (command == "run") {
            bf->run();
        }
        else if (command == "read") {
            bf->output();
            cout << endl;
        }
        else {
            // 2 part commands
            // all commands have the second part as an integer

            // find seperator
            auto pos = command.find(" ");

            if (pos != string::npos) {
                string sub_num = command.substr(pos+1, command.length());
                if (!all_of(sub_num.begin(), sub_num.end(), ::isdigit)) {
                    std::cout << "Unknown command" << endl;
                    continue;
                }
                
                unsigned int num = stoi(sub_num);
                command = command.substr(0, pos);

                if (command == "run") {
                    bf->execute(num);
                }
                else if (command == "debug") {
                    bf->set_debug_mode((bool)num);
                }
                else if (command == "br") {
                    bf->new_br(num);
                }
                else if (command == "unbr") {
                    bf->remove_br(num);
                }
                else {
                    std::cout << "Unknown command" << endl;
                }
            }
            else {
                std::cout << "Unknown command" << endl;
            }
        }
    }

    if (bf->is_finished()) {
        std::cout << "Program finished" << endl;
    }

    delete bf;
}

void exit_sig_handler(int) noexcept {
    cout << "Caught termination signal exiting" << endl;
    exit(1);
}

int main(int argc, char* argv[]) {
    if (argc > 2) {
        cout << "Usage: '" << argv[0] << "' <brainfuck code path>\nOr '" << argv[0] << "' for interactive mode'";
    }

    int exit_code = 0;

    // register signal handlers for terminating infinite programs gracefully on ctrl+C
    signal(SIGINT, exit_sig_handler);

    if (argc == 1) {
        // if not arguement given use interactive mode
        interactive_mode();
        return 0;
    }

    try {
        // file path given in command line
        // run bf code to completion (or error)
        Interpreter bf(argv[1]);
        bf.run();
    }
    catch (const exception& e) {
        cout << e.what() << endl;
        exit_code = 1;
    }

    system("pasus");

    return exit_code;
}

void Interpreter::input() {
    // read input from user into pointed cell
    *tape_iterator = (unsigned char) getchar();
}

void Interpreter::output() const {
    // print pointed cell
    putchar(*tape_iterator);
}

bool Interpreter::step() {
    // executes the pointer command and increment pointer
    // pointer is incremented after execution so pointer always points to the next command
    switch (commands[command_pointer]) {
    case (Command::inc):
        ++(*tape_iterator);
        break;
    case (Command::dec):
        --(*tape_iterator);
        break;
    case (Command::left):
        if (tape_iterator == tape.begin()) {
            throw TapeLeftBound();
        }
        --tape_iterator;
        break;
    case (Command::right):
        ++tape_iterator;
        if (tape_iterator == tape.end()) {
            // add new cells to the tape on demand
            tape.push_back((unsigned char) 0);
            // this is the only place that modifies the tape size
            // so get a new iterator since the old is invalid
            tape_iterator = tape.end();
            --tape_iterator;
        }
        break;
    case (Command::out):
        this->output();
        break;
    case (Command::in):
        this->input();
        break;
    case (Command::open):
        // jump forward if zero
        if (!(*tape_iterator)) {
            command_pointer = forward_jumps[command_pointer];
        }
        break;
    case (Command::close):
        // jump backwards if not zero
        if (*tape_iterator) {
            command_pointer = backward_jumps[command_pointer];
        }
        break;
    }

    ++command_pointer;

    // return true when there is a breakpoint on the next instruction
    return (breakpoints.find(command_pointer) != breakpoints.end());
}

Interpreter::Interpreter(const string& bf_path) : bf_path(bf_path), debug_mode(false), commands(0), tape(1000, 0), forward_jumps(), backward_jumps(), breakpoints(), command_pointer(0), tape_iterator(tape.begin()) {
    char next;
    ifstream file(this->bf_path, fstream::in);
    // check file is valid
    if (!file) {
        throw runtime_error("Could not open file " + this->bf_path);
    }

    pointer_t running_pointer = 0;

    // stack to track branches relations
    // push on the stack when encoutering '['
    // pop and create relation on ']'
    stack<pointer_t> branch_stack;

    // read the input file and parse tokens
    while (file.get(next)) {
        switch (next) {
        case ('+'):
            commands.push_back(Command::inc);
            break;
        case ('-'):
            commands.push_back(Command::dec);
            break;
        case ('<'):
            commands.push_back(Command::left);
            break;
        case ('>'):
            commands.push_back(Command::right);
            break;
        case ('.'):
            commands.push_back(Command::out);
            break;
        case (','):
            commands.push_back(Command::in);
            break;
        case ('['):
            commands.push_back(Command::open);
            branch_stack.push(running_pointer);
            break;
        case (']'):
            commands.push_back(Command::close);
            // check stack is not empty
            if (branch_stack.empty()) {
                throw UnbalancedBracket();
            }
            // create jump pair
            forward_jumps.insert(pair<pointer_t, pointer_t>(branch_stack.top(), running_pointer));
            backward_jumps.insert(pair<pointer_t, pointer_t>(running_pointer, branch_stack.top()));
            branch_stack.pop();
            break;
        case ('!'):
            // breakpoint is ignored for commands array
            // need to decrement the running pointer to offset the breakpoint
            // postfix decrement will insert the breakpoint at the correct index
            new_br(running_pointer--);
            // because breakpoint is not a command
            break;
        default:
            // all other chars are ignored
            break;
        }

        ++running_pointer;
    }

    // after program parsed need to ensure branch stack is empty
    if (!branch_stack.empty()) {
        throw UnbalancedBracket();
    }

    file.close();
}

Interpreter & Interpreter::execute(unsigned int count) {
    for (unsigned int i = 0; (i < count) && (command_pointer < commands.size()); ++i) {
        bool is_br = step();
        if (debug_mode && is_br) {
            break;
        }
    }

    if (command_pointer == commands.size()) {
        cout << "\nProgram finished successfully" << endl;
    }

    return *this;
}

Interpreter & Interpreter::run() {
    while (command_pointer < commands.size()) {
        bool is_br = step();
        if (debug_mode && is_br) {
            return *this;
        }
    }

    cout << "\nProgram finished successfully" << endl;

    return *this;
}

Interpreter & Interpreter::new_br(pointer_t at) {
    breakpoints.insert(at);
    return *this;
}

Interpreter & Interpreter::remove_br(pointer_t at) {
    auto it = breakpoints.find(at);
    if (it != breakpoints.end()) {
        breakpoints.erase(it);
    }
    else {
        cout << "No breakpoint found at " << at << endl;
    }
    
    return *this;
}

bool Interpreter::is_finished() const {
    return command_pointer == commands.size();
}

void Interpreter::set_debug_mode(bool mode) {
    debug_mode = mode;
}
