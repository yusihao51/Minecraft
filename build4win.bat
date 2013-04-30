@echo off
echo Setting tools to VS2012...
SET VS90COMNTOOLS=%VS110COMNTOOLS%
echo Clearing old compile files (if the exist)...
del *.pyc 
del *.c
del *.h
del *.so
echo Doing a fresh compile...
python setup.py build --compiler=msvc
echo Packaging for Windows (w/o dependents...)
python setup.py bdist_wininst
echo Done.
@echo on
