#include <iostream>
#include <string>
#include <cstdio>
#include <algorithm>
#include <fstream>
#include <stack>
#include <csignal>
#include "interpreter.h"

using namespace std;

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

    system("pause");

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
    (*command_iterator->first)();
    ++command_iterator;

    // return true when there is a breakpoint on the next instruction
    return ((command_iterator != commands.end()) && (*command_iterator).second);
}

Interpreter::Interpreter(const string& bf_path) : bf_path(bf_path), debug_mode(false), commands(0), tape(10, 0), command_iterator(commands.begin()), tape_iterator(tape.begin()) {
    char next, peeked;
    ifstream file(this->bf_path, fstream::in);
    // check file is valid
    if (!file) {
        throw runtime_error("Could not open file " + this->bf_path);
    }

    Command* cmd;

    // used to count consecutive character that can be merged
    int count = 0;

    // stack to track branches relations
    // push on the stack when encoutering '['
    // pop and create relation on ']'
    stack<int> branch_stack;

    // read the input file and parse tokens
    while (file.get(next)) {
        switch (next) {
        case ('+'):
        case ('-'):
            count = (next == '+') ? 1 : -1;
            peeked = file.peek();
            while ((peeked == '+' || peeked == '-')) {
                file.get(next);     // will always read either + or -
                count += (next == '+') ? 1 : -1;
                peeked = file.peek();
            }
            cmd = new AddCommand(tape, tape_iterator, count);
            commands.push_back(pair<Command*, bool>(cmd, 0));
            break;
        case ('<'):
        case ('>'):
            count = (next == '>') ? 1 : -1;
            peeked = file.peek();
            while ((peeked == '<' || peeked == '>')) {
                file.get(next);     // will always read either < or >
                count += (next == '>') ? 1 : -1;
                peeked = file.peek();
            }
            cmd = new MoveCommand(tape, tape_iterator, count);
            commands.push_back(pair<Command*, bool>(cmd, 0));
            break;
        case ('.'):
            cmd = new OutputCommand(tape, tape_iterator);
            commands.push_back(pair<Command*, bool>(cmd, 0));
            break;
        case (','):
            cmd = new InputCommand(tape, tape_iterator);
            commands.push_back(pair<Command*, bool>(cmd, 0));
            break;
        case ('['):
            branch_stack.push(commands.size());
            cmd = new JmpCommand(tape_iterator, command_iterator);
            commands.push_back(pair<Command*, bool>(cmd, 0));
            break;
        case (']'):
            if (branch_stack.empty()) {
                throw UnbalancedBracket();
            }
            // create the backward jump command
            // and modify the forward branch

            // backward jump
            cmd = new JmpCommand(tape_iterator, command_iterator);
            static_cast<JmpCommand*>(cmd)->set_offset(branch_stack.top() - (int) commands.size());

            // forward jump
            static_cast<JmpCommand*>(commands[branch_stack.top()].first)->set_offset(commands.size() - branch_stack.top());

            commands.push_back(pair<Command*, bool>(cmd, 0));
            branch_stack.pop();
            break;
        default:
            // all other chars are ignored
            break;
        }
    }

    // after program parsed need to ensure branch stack is empty
    if (!branch_stack.empty()) {
        throw UnbalancedBracket();
    }

    file.close();

    // get a new valid iterator for commands
    command_iterator = commands.begin();
}

Interpreter::~Interpreter() {
    // deallocate all the commands
    for (auto it : commands) {
        delete it.first;
    }
}

Interpreter & Interpreter::execute(unsigned int count) {
    for (unsigned int i = 0; (i < count) && (!this->is_finished()); ++i) {
        bool is_br = step();
        if (debug_mode && is_br) {
            break;
        }
    }

    if (command_iterator == commands.end()) {
        cout << "\nProgram finished successfully" << endl;
    }

    return *this;
}

Interpreter & Interpreter::run() {
    while (!this->is_finished()) {
        bool is_br = step();
        if (debug_mode && is_br) {
            return *this;
        }
    }

    cout << "\nProgram finished successfully" << endl;

    return *this;
}

Interpreter & Interpreter::new_br(size_t at) {
    commands[at].second = true;
    return *this;
}

Interpreter & Interpreter::remove_br(size_t at) {
    commands[at].second = false;
    return *this;
}

bool Interpreter::is_finished() const {
    return command_iterator == commands.end();
}

void Interpreter::set_debug_mode(bool mode) {
    debug_mode = mode;
}
