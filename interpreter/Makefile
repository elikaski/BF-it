interpreter: interpreter.o
	g++ interpreter.o command.o -o interpreter

interpreter.o: interpreter.cpp interpreter.h command.cpp command.h
	g++ -c interpreter.cpp command.cpp -std=c++11 -O2 -s -Wall -Wextra -pedantic -Weffc++
