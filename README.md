# BF-it
A compiler from a C-like language to Brainfuck


Always heard that brainfuck is turing complete but still had doubts about its computational power?
Those days are over


## What is this?
BF-it is a Compiler of a C-like language to Brainfuck, written in Python

You give it C-like code, and it gives you Brainfuck code with the same functionality :)


## Why did you create it?
There are several reasons why I chose to create this
```
1. I always heard that brainfuck is turing complete, and therefore as strong as any other language
	I wanted to put that to the test, and find a concrete proof that it is true
2. I find it beautiful how a seemingly bunch of nonsense characters can have a logical meaning / functionality
	I wanted to take it to the extreme
3. I wanted to practice my developing skills
4. It seemed to be like a real challenge (and it was!)
5. But mostly, and most importantly, I did it for teh lulz
```

## What can I use it for?
Create a brainfuck code of your choice, send it to your friends, and tell them to run it (on some online interpreter, for example)

When they receive a bunch of nonsense which does something meaningful, they will (maybe) be amazed


## How do I use it?
First of all, write a C-like code (example programs included)

METHOD 1 (my preferred)
```
1. Open Compiler.py in your favorite IDE (I use PyCharm)
2. Edit the __main__ section to contain your code
3. Run Compiler.py
```

METHOD 2
```
1. Open your favorite command line interface (I use Windows's cmd)
2. Put your code in a file
3. Run "python Compiler.py <path_to_code_file>"
	This will compile your file and create a .bf file with brainfuck code
4. Run "python Interpreter.py <path_to_bf_file>"
	This will execute the brainfuck code
```

## I would like to add a feature / fix a bug
If you would like to add a feature yourself, perform a pull request and add your changes. I will review them

If you found a bug, or have an idea for a feature, open an issue



## References I used:
* https://esolangs.org/wiki/brainfuck_algorithms for basic Brainfuck algorithms
* https://www.iamcal.com/misc/bf_debug/ for debugging Brainfuck code
* https://fatiherikli.github.io/brainfuck-visualizer/ for debugging Brainfuck code
* https://godbolt.org/ for comparing my C-like compiler to other C compilers' implementation
* https://www.lysator.liu.se/c/ANSI-C-grammar-y.html for creating a grammar
* https://introcs.cs.princeton.edu/java/11precedence/ for operator precedence
* https://www.youtube.com/ for setting the mood

	
	
## I like it! how can I give you money?
If you like it, you can donate me some money

If you choose to donate, I will use your money to buy myself non-dairy ice cream

With a flavor of your choosing

And will email you a picture of it as proof
	
[![paypal](https://www.paypalobjects.com/en_US/i/btn/btn_donateCC_LG.gif)](https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=F9A8U8H2F7QKJ)

