from pylogfile import *

fmt = LogFormat()
fmt.show_detail = True
log = LogPile(str_fmt=fmt)

log.info("This is some >spicy< information.", detail="lkasdhfjklghasdfbasdfljkhasklasdf")
log.debug("10001010>:31011<101")
log.warning("Spooky scary", detail="lbasdfpjklASDF asd jkhAS DJKL asd jklhgdf aslg")
log.error("This is an error!")
log.critical("Oh no I'm dead XX", detail="asdfjklhasdfb jkasdfasdjkfasdkfjhasdjklg")
print(f"\n\n")

log.save_hdf("test.log.hdf")
log.save_json("test.log.json")

print(f"READING JSON")
log2 = LogPile(str_fmt=fmt)
if not log2.load_json("test.log.json"):
	print("Failed to read JSON")
log2.show_logs()
print(f"\n\n")

print(f"READING HDF")
log3 = LogPile(str_fmt=fmt)
if not log3.load_hdf("test.log.hdf"):
	print("\tFailed to read HDF")
log3.show_logs()