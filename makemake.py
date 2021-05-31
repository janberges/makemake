#!/usr/bin/env python3

import os
import re
import sys

args = {
    'bin': '.',
    'src': '.',
    'obj': '.',
    'mod': '.',
    }

for arg in sys.argv[1:]:
    if '=' in arg:
        key, value = arg.split('=')

        if key in args:
            args[key] = value

preamble = ''

if os.path.exists('makefile'):
    with open('makefile') as makefile:
        for line in makefile:
            if 'generated by makemake' in line:
                break

            preamble += line
        else:
            print('Unknown Makefile already exists')
            raise SystemExit

preamble = preamble or '''
FC = gfortran

flags_gfortran = -std=f2008 -Wall -pedantic
flags_ifort = -O0 -warn all

FFLAGS = ${{flags_$(FC)}}

# exception.o: FFLAGS += -Wno-maybe-uninitialized
# LDLIBS = -llapack -lblas

modules_gfortran = -J{0}
modules_ifort = -module {0}

override FFLAGS += ${{modules_$(FC)}}

needless = {0}/*.mod
'''.format(args['mod'])

preamble = preamble.strip()

references = {}
companions = {}
components = {}

folders = [args['src']]

for folder in folders:
    for file in os.listdir(folder):
        if file.startswith('.'):
            continue

        path = folder + '/' + file

        if os.path.isdir(path):
            folders.append(path)

        elif path.endswith('.f90'):
            doto = re.sub('^%s/' % args['src'], '%s/' % args['obj'], path)
            doto = re.sub(r'\.f90$', '.o', doto)

            references[doto] = set()

            with open(path) as code:
                for line in code:
                    match = re.match(r'\s*(use|program|module)'
                        r'\s+(\w+)\s*(?:$|,)', line, re.I)

                    if match:
                        statement, name = match.groups()

                        if statement == 'use':
                            references[doto].add(name)

                        elif statement == 'module':
                            companions[name] = doto

                        elif statement == 'program':
                            components['%s/%s' % (args['bin'], name)] = {doto}

for target, modules in references.items():
    references[target] = set(companions[name]
        for name in modules if name in companions)

related = set()

for doto in components.values():
    todo = list(doto)

    for target in todo:
        new = references[target] - doto

        doto |= new
        todo += new

    related |= doto

for target in list(references.keys()):
    if target not in related:
        del references[target]

def join(these):
    return ' '.join(sorted(these))

programs = join(components)
adjuncts = join(related)

def listing(dependencies):
    return '\n'.join(target + ': ' + join(doto)
        for target, doto in sorted(dependencies.items()) if doto)

components = listing(components)
references = listing(references)

content = '''

# generated by makemake.py:

programs = {programs}

.PHONY: all clean cleaner

all: $(programs)

clean:
\trm -f $(needless) {adjuncts}

cleaner: clean
\trm -f $(programs)

$(programs):
\t$(FC) -o $@ $^ $(LDLIBS)

{args[obj]}/%.o: {args[src]}/%.f90
\t$(FC) $(FFLAGS) -c $< -o $@

{components}

{references}
'''.format(**vars())

content = re.sub(r'(^|\s)\./', r'\1', content)

with open('makefile', 'w') as makefile:
    makefile.write(preamble)
    makefile.write(content)
