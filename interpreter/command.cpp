#include "command.h"
#include <iostream>
#include <iterator>

using namespace std;

TapeCommand::TapeCommand(vector<unsigned char>& tape, vector<unsigned char>::iterator& tape_iter) : Command(), tape(tape), tape_iterator(tape_iter) {}

MoveCommand::MoveCommand(vector<unsigned char>& tape, vector<unsigned char>::iterator& tape_iter, int move_count) : TapeCommand(tape, tape_iter), count(move_count) {}

AddCommand::AddCommand(vector<unsigned char>& tape, vector<unsigned char>::iterator& tape_iter, int add) : TapeCommand(tape, tape_iter), count(add) {}

InputCommand::InputCommand(vector<unsigned char>& tape, vector<unsigned char>::iterator& tape_iter) : TapeCommand(tape, tape_iter) {}

OutputCommand::OutputCommand(vector<unsigned char>& tape, vector<unsigned char>::iterator& tape_iter) : TapeCommand(tape, tape_iter) {}


void MoveCommand::operator()() {
	// distance is constant time for random access iterator (which a vector iterator is)
	auto dist_to_end = distance(tape_iterator, tape.end());
	auto dist_to_start = distance(tape_iterator, tape.begin());

	if (dist_to_start > count) {
		throw TapeLeftBound();
	}

	if (dist_to_end <= count) {
		tape.insert(tape.end(), count - dist_to_end + 1, 0);
		tape_iterator = tape.end();
		--tape_iterator;
		return;
	}

	tape_iterator += count;
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

JmpCommand::JmpCommand(vector<unsigned char>::iterator& tape_iter, vector<pair<Command*, bool>>::iterator& command_iter) : tape_iterator(tape_iter), command_iterator(command_iter), offset(0) {}

void JmpCommand::set_offset(int offset) {
	this->offset = offset;
}

void JmpCommand::operator()() {
	// offset can tell us if it's a forward or backwards branch
	// forward jump should happen if zero, backward if not

	unsigned char tape_val = *tape_iterator;

	if (((offset > 0) && (!tape_val)) || ((offset < 0) && (tape_val))) {
		command_iterator += offset;
	}
}
