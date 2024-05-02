from pylogfile import *

fmt = LogFormat()
fmt.show_detail = True
log = LogPile(str_fmt=fmt)

log.info("This is some >spicy< information.", detail="lkasdhfjklghasdfbasdfljkhasklasdf")
log.debug("10001010>:31011<101")
log.warning("Spooky scary", detail="lbasdfpjklASDF asd jkhAS DJKL asd jklhgdf aslg")
log.error("This is an error!")
log.critical("Oh no I'm dead XX", detail="asdfjklhasdfb jkasdfasdjkfasdkfjhasdjklg")

