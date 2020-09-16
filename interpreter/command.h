#pragma once
#include <list>
#include <vector>
#include <unordered_map>

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
	std::list<unsigned char>& tape;
	std::list<unsigned char>::iterator& tape_iterator;
public:
	TapeCommand(std::list<unsigned char>& tape, std::list<unsigned char>::iterator& tape_iter);
	TapeCommand(const TapeCommand& other);	
	virtual void operator()() = 0;
	virtual ~TapeCommand() {}
};

class MoveCommand : public TapeCommand {
	int count;
public:
	MoveCommand(std::list<unsigned char>& tape, std::list<unsigned char>::iterator& tape_iter, int move_count);
	virtual void operator()();
	virtual ~MoveCommand() {}
};

class AddCommand : public TapeCommand {
	int count;
public:
	AddCommand(std::list<unsigned char>& tape, std::list<unsigned char>::iterator& tape_iter, int add);
	virtual void operator()();
	virtual ~AddCommand() {}
};

class InputCommand : public TapeCommand {
public:
	InputCommand(std::list<unsigned char>& tape, std::list<unsigned char>::iterator& tape_iter);
	virtual void operator()();
	virtual ~InputCommand() {}
};

class OutputCommand : public TapeCommand {
public:
	OutputCommand(std::list<unsigned char>& tape, std::list<unsigned char>::iterator& tape_iter);
	virtual void operator()();
	virtual ~OutputCommand() {}
};

class JmpCommand : public Command {
protected:
	std::list<unsigned char>::iterator& tape_iterator;
	std::vector<std::pair<Command*, bool>>::iterator& command_iterator;
	int offset;
public:
	JmpCommand(std::list<unsigned char>::iterator& tape_iter, std::vector<std::pair<Command*, bool>>::iterator& command_iter);
	void set_offset(int offset);
	virtual void operator()();
	virtual ~JmpCommand() {}
};
