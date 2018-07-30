rem Start Arelle XBRL COM server

@set PYTHONDIR=C:\Users\deepak.khopade\AppData\Local\Programs\Python\Python35\
@set PYTHONPATH=..

"%PYTHONDIR%\python" -m arelle.CntlrCmdLine --webserver localhost:8080
PAUSE