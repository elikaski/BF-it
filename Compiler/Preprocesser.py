""" This is the preprocessor. This is the bit of code that handles the
#include and #define. Pretty simple, and the algorithms are quite naive. """

class Preprocesser:
  def preprocess(code):
    to_preprocess = code.split(" ")
		in_string = False
    for token in to_preprocess:
	if ('"', "'") in token:
		in_string = not in_string
	if not in_string:
		if token == '#include':
			file = to_preprocess[i + 1].replace('<', '').replace('>', '')
			with open(file, 'r') as f:
				code_include = f.read()
			code.replace(f'#include <{file}>', code_include)
		 elif token == '#define':
			define_name = to_preprocess[i + 1]
			define_val = to_preprocess[i + 2]
			code.replace(define_name, define_val)
		 else:
			continue
