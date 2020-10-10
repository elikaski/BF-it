#pragma once
#include <vector>

class TapeLeftBound : public std::exception {
	virtual const char* what() const throw() {
		return "Tape pointer tried leaving tape";
	}
};

class Command {
public:
	virtual void operator()() = 0;
	virtual ~Command() {}
};

class TapeCommand : public Command {
protected:
	std::vector<unsigned char>& tape;
	std::vector<unsigned char>::iterator& tape_iterator;
public:
	TapeCommand(std::vector<unsigned char>& tape, std::vector<unsigned char>::iterator& tape_iter);
	virtual void operator()() = 0;
	virtual ~TapeCommand() {}
};

class MoveCommand : public TapeCommand {
	int count;
public:
	MoveCommand(std::vector<unsigned char>& tape, std::vector<unsigned char>::iterator& tape_iter, int move_count);
	virtual void operator()();
	virtual ~MoveCommand() {}
};

class AddCommand : public TapeCommand {
	int count;
public:
	AddCommand(std::vector<unsigned char>& tape, std::vector<unsigned char>::iterator& tape_iter, int add);
	virtual void operator()();
	virtual ~AddCommand() {}
};

class InputCommand : public TapeCommand {
public:
	InputCommand(std::vector<unsigned char>& tape, std::vector<unsigned char>::iterator& tape_iter);
	virtual void operator()();
	virtual ~InputCommand() {}
};

class OutputCommand : public TapeCommand {
public:
	OutputCommand(std::vector<unsigned char>& tape, std::vector<unsigned char>::iterator& tape_iter);
	virtual void operator()();
	virtual ~OutputCommand() {}
};

class JmpCommand : public Command {
protected:
	std::vector<unsigned char>::iterator& tape_iterator;
	std::vector<std::pair<Command*, bool>>::iterator& command_iterator;
	int offset;
public:
	JmpCommand(std::vector<unsigned char>::iterator& tape_iter, std::vector<std::pair<Command*, bool>>::iterator& command_iter);
	void set_offset(int offset);
	virtual void operator()();
	virtual ~JmpCommand() {}
};
