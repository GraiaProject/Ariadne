import graia.ariadne.event.lifecycle
import graia.ariadne.event.message
import graia.ariadne.event.mirai
import graia.ariadne.event.network

# init event

ARIADNE_ASCII_LOGO = r"""
                _           _            
     /\        (_)         | |           
    /  \   _ __ _  __ _  __| |_ __   ___ 
   / /\ \ | '__| |/ _` |/ _` | '_ \ / _ \
  / ____ \| |  | | (_| | (_| | | | |  __/
 /_/    \_\_|  |_|\__,_|\__,_|_| |_|\___|
""".lstrip(
    "\n"
)
# remove first newline


TELEMETRY_LIST = ["graia-ariadne", "graia-broadcast", "graia-scheduler", "graia-saya"]
