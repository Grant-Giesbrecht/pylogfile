from pylogfile.base import *

fmt = LogFormat()
fmt.show_detail = True
log = LogPile(str_fmt=fmt)

log.info("This is some >spicy< information.", detail="lkasdhfjklghasdfbasdfljkhasklasdf")
log.debug("10001010>:31011<101")
log.warning("Spooky scary", detail="lbasdfpjklASDF asd jkhAS DJKL asd jklhgdf aslg")
log.error("This is an error!")
log.critical("Oh no I'm dead XX", detail="asdfjklhasdfb jkasdfasdjkfasdkfjhasdjklg")
print(f"\n\n")

log.save_plflog("test.plflog")
# log.save_json("test.log.json")

# print(f"READING JSON")
# log2 = LogPile(str_fmt=fmt)
# if not log2.load_json("test.log.json"):
# 	print("Failed to read JSON")
# log2.show_logs()
# print(f"\n\n")

print(f"READING HDF")
log3 = LogPile(str_fmt=fmt)
if not log3.load_plflog("test.plflog"):
	print("\tFailed to read HDF")
log3.show_logs()

print(f"v0 Test")
log.save_plflog("test_v0.plflog", file_version="0.0")

log4 = LogPile(str_fmt=fmt)
if not log4.load_plflog("test_v0.plflog"):
	print("\tFailed to read HDF")
log4.show_logs()

# log5 = LogPile(str_fmt=fmt)
# if not log5.load_plflog("DP1a_dd0B.log.hdf"):
# 	print("\tFailed to read HDF")
# log5.show_logs()

# log3.make_level("new_debug", 14)