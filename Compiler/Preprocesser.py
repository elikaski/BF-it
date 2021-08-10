class Preprocesser:
  def preprocess(code):
    to_preprocess = code.split(" ")
    for i in range(0, len(to_preprocess)):
      token = to_preprocess[i]
      if token in ('#include', '#define'):
        if token == '#include':
          file = to_preprocess[i + 1].replace('<', '').replace('>', '')
          f = open(file, 'r')
          code_include = f.read()
          code.replace(f'#include <{file}>', code_include)
         elif token == '#define':
          define_name = to_preprocess[i + 1]
          define_val = to_preprocess[i + 2]
          code.replace(define_name, define_val)
          

