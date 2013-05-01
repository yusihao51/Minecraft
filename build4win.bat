@echo off
echo Setting tools to VS2012...
SET VS90COMNTOOLS=%VS110COMNTOOLS%
echo Clearing old compile files (if they exist)...
del *.c
del *.h
echo Doing a fresh compile...
python setup.py build --compiler=msvc
echo Packaging for Windows (w/o dependents...)
python setup.py bdist_wininst
echo Done.
echo Cleaning up...
del *.c
del *.h
@echo on
