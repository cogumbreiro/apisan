#!/usr/bin/env python3
import sys
import os
import string

def main():
    with open(sys.argv[1]) as fp:
        data = fp.read()
        doc = string.Template(data)
        sys.stdout.write(doc.substitute(PWD=os.getcwd()))
    

if  __name__ == '__main__':
    main()

