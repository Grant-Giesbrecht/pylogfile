from pylogfile.base import *
from colorama import Fore, Style

fmt = LogFormat()
fmt.show_detail = True
log = LogPile(str_fmt=fmt)

log.info("This is some >spicy< information.", detail="lkasdhfjklghasdfbasdfljkhasklasdf")
log.debug("10001010>:31011<101")
log.warning("Spooky scary", detail="lbasdfpjklASDF asd jkhAS DJKL asd jklhgdf aslg")
log.error("This is an error!")
log.critical("Oh no I'm dead XX", detail="asdfjklhasdfb jkasdfasdjkfasdkfjhasdjklg")
log.lowdebug(f"This is a low debug message.")
print(f"\n\n")

print(f"This is what logs look like when printed without overrides.")
log.show_logs()

fmt.color_overrides = {10:{'label':Fore.MAGENTA, 'main':Fore.RED}, 20:{'label':Fore.MAGENTA, 'main':Fore.RED}, 30:{'label':Fore.MAGENTA, 'main':Fore.RED}, 40:{'label':Fore.MAGENTA, 'main':Fore.RED}, 50:{'label':Fore.MAGENTA, 'main':Fore.RED} }

print(f"\n\nNow I'm going to override all the levels except low debug to print red text and purple labels.")
log.show_logs()