import subprocess
import sys
i = sys.argv[1];
subprocess.call(["./appletanalysis.sh", "appletanalysis.py", i, "test.out"])
o = open("test.out")
line = o.readline()
o.close()
if "malicious" in line:
	print(str(line))
	if i[-4:] == ".jar":
		basename = str(subprocess.check_output(["basename", i, ".jar"])).strip()
	else:
		basename = str(subprocess.check_output(["basename", i, ".class"])).strip()
	subprocess.call(["rm", "-rf", basename])
else:
	subprocess.call(["./appletanalysis.sh", "jarhead.py", i, "test.out"])
	o = open("test.out")
	line = o.readline().strip()
	if line == "malicious":
		print("malicious")
	else:
		print("benign")
	o.close()
subprocess.call(["rm", "-f", "test.out"])
