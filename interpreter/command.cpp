#include "command.h"
#include <iostream>
using namespace std;

TapeCommand::TapeCommand(list<unsigned char>& tape, list<unsigned char>::iterator& tape_iter) : Command(), tape(tape), tape_iterator(tape_iter) {}

MoveCommand::MoveCommand(list<unsigned char>& tape, list<unsigned char>::iterator& tape_iter, int move_count) : TapeCommand(tape, tape_iter), count(move_count) {}

AddCommand::AddCommand(list<unsigned char>& tape, list<unsigned char>::iterator& tape_iter, int add) : TapeCommand(tape, tape_iter), count(add) {}

InputCommand::InputCommand(std::list<unsigned char>& tape, std::list<unsigned char>::iterator& tape_iter) : TapeCommand(tape, tape_iter) {}

OutputCommand::OutputCommand(std::list<unsigned char>& tape, std::list<unsigned char>::iterator& tape_iter) : TapeCommand(tape, tape_iter) {}


void MoveCommand::operator()() {
	// count can be either positive or negative
	for (int i = 0; i < count; ++i) {
		++tape_iterator;
		// only enters if count is positive (move right)
		if (tape_iterator == tape.end()) {
			// in this case we add all the needed elements at once
			// moving the tape pointer to the end and finish this function
			tape.insert(tape.end(), (size_t)count - i, 0);
			tape_iterator = tape.end();
			--tape_iterator;
			return;
		}
	}
	for (int i = 0; i > count; --i) {
		if (tape_iterator == tape.begin()) {
			throw TapeLeftBound();
		}
		--(tape_iterator);
	}
}

void AddCommand::operator()() {
	*tape_iterator += (unsigned char) count;
}

void InputCommand::operator()() {
	*tape_iterator = (unsigned char) getchar();
}

void OutputCommand::operator()() {
	putchar(*tape_iterator);
}

JmpCommand::JmpCommand(std::list<unsigned char>::iterator& tape_iter, std::vector<std::pair<Command*, bool>>::iterator& command_iter) : tape_iterator(tape_iter), command_iterator(command_iter), offset(0) {}

void JmpCommand::set_offset(int offset) {
	this->offset = offset;
}

void JmpCommand::operator()() {
	// offset can tell us if it's a forward or backwards branch
	// forward jump should happen if zero, backward if not
	// can be written as a xor

	unsigned char tape_val = *tape_iterator;

	if ((offset > 0) && (!tape_val)) {
		command_iterator += offset;
	}

	if ((offset < 0) && (tape_val)) {
		command_iterator += offset;
	}
}
