# Copyright (c) 2018 by Software.com

from threading import Thread, Timer, Event
from package_control import events
from queue import Queue
import webbrowser
import time
import datetime
import json
import os
import sublime_plugin, sublime
from .lib.SoftwareHttp import *
from .lib.SoftwareUtil import *
from .lib.SoftwareMusic import *
from .lib.SoftwareRepo import *
from .lib.SoftwareOffline import *
from .lib.SoftwareSettings import *

DEFAULT_DURATION = 60

SETTINGS = {}

PROJECT_DIR = None

check_online_interval_sec = 60 * 10
retry_counter = 0

#TODO: store this offline?
icons = {
    "bolt-grey": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAACXBIWXMAACxLAAAsSwGlPZapAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAKkSURBVHgB7dpPbtNAFAbw742D1GWP4BuQGxBOUBcJKWKXI3CDcgM4Qc0uCKkYxB4fAW7gG5AdLOJ5TEqLSqhjO+/Ns1Dnt6nUWEry2fPnvQmQJEmSJMlDRVBUFC/mTO0liOYYr2Gg/HS1fgVDDorY+Q9HfvmdPNyNi6IoTmFILYCbD55DaIuTYwM8iuIT8CiHgs/VuoYhtQC2GeWQYtQwphbAjLMcQp7oI4ypBeBZPv4zv61hTC0AAj+GTFNV77/CmN4k6Fi0fDHzN0xALwAm0fLliCpMQCWAoljmkPL2K8CO1hOQQyaM/3WDCagE0MoDqDERlQDIyQIgb7/+39IJgKRL4I8aE5lBg6dTSWHN7uT72bPl0Msb8u251p5BZxIksqzgcqbZJZSIA/hdBrNpDQ9itcAVngCdMnikEkrEAaiUweOEOQBqbTNxABpl8Bihb/hWc9MkDkCjDB6hCU3TCygSB6BQBo94L6h3jOWToLNaAbiqrtYllMkDYJs9QNguv0QE8gCILbo4ZaxqUT4HtNkq/GkQj+qyt0/1aGyos/Pll/DOiyHXhg+4ijH2b6kejQ02vHZoYn75HfMAQvtsMbR2aD1WiMz+CXCD735pcUxmHgCTfzLkupgT3132TwC7Re8lYcdn1SQ1DaAons8HjP/G+Z+vYcQ0gBZZ7/in67tfbWDENADn0Df+oy97+6zngMWhF8PE9xTGzAK4OT7LD1xSTnE6ZBbANvMHxj9trJa9fWYBOJ8tul5j8Jv/+mxwCHKdGyD1NtcYJgFcnx10NE5itLnG0Dka69X1279dm+tdiQmZPAGeqLjv/7HaXGOYBNDROS6nmvjuspkE/+3+NFMte/uMAvi7cUqG1V4fmyHwp3FKG+aw5hvv95MkSZIkSe7zC7hNx9RHEqHkAAAAAElFTkSuQmCC",
    "bolt": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAACXBIWXMAACxLAAAsSwGlPZapAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAKwSURBVHgB7ZpRbtNAEIb/jZ1ISDyUG/gRISpyg9o3gCPkCNyA3gBO0HCDcgL7CAEqXukNyFulxvbgEaooUeLuambHVN3vJUpsJfHvmfl3xgskEolEIpF4qjgoclu/WjqXXwC0RCDDH7km59bzs2/nMERVgLY5/UlAAQE5ZS9ctdnCiBmUoHp5Ir14pkUbHD0S1ATY4baAAvPqqoEhagLMkBUQQw2MUROgRV9ASEf0BcYoRoArIKR9zBHgnHsDAWyDz6sfGxijJsCQvycQ0BG+YgIUBXAi+xoi4BIToCLATb0sIKRD1mACVATI0RYQwPn/rNpcYwJUBCC4AjIaTISSAFRAwFAAzf3/DhUBZkILXEyU/0wOHUQW2Lru16459TqX60VP3buF0ppBywbNOjjuOJ2bXUAJsQDcBkMYAeE4NcHFAmi1wSEMabCGEmIBdNpgf7gG7ChTG5uJBdBog0Mgos+aiyaxC2i0wb7w3c+rqw9QRBwB0jY4hJ6gPjFWsEEycgC6XFTf11BGQQBnsgZoKX+PCGhEQPQpDtterG5RvhCifsXFCZHQtr0D32/PsO6vh5fS51wirGLk/h1azVAoXnWD7/484sUzijNBP3b16xKevcOw6FkhMuYCdJ5PjrnwWTwmMxcgc7Mzn/NiFr77mAsAn+JHdG41JDUtgryBAg/kPxe+DPlHGGEcAdmD+c/r/Ue5QcLrxxxG85/v/iKy7e1jXQPKsYND4atgjJkAN/XLYmwLTcz1/hhmAswxH8v/rZXt7WMmQA8qjx4k+jTVs0EzG3RHCmCMMVcIJhHw59nB4cFJjDFXCCYCHN/7F2fMFYJNBABvD30ea8wVgokAhybHU9nePlYuUN5/E3vMFYKRAP8OTrnw/Q93n7GpAX8Hp1v2/KkLXyKRSCQSiQTzGxKu0AZA9tcvAAAAAElFTkSuQmCC",
    "commit": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAACXBIWXMAACxLAAAsSwGlPZapAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAL3SURBVHgB7dnNTlNBFAfw/5m6qDvewLokMZG+QdmTdCDRVDeWJwCeANi55QmEjTYxobfqnj5CTUhkZ9/A7nQBczxzKSSS+9XrzI2J55cQmt7ejznzcWbmAkoppZRSSimllFJKqf8JoUFbdtAzhvvEtCF37shXneVjLMA8Y+KZczT5koymaEgjAdiyL22LzJ7crVfxlLkDjj+fj04RWdQAWDvoMOHdCgX/E2NKjN0kGc0RSbQAWPt6g40b476Z1zYnh81YQYgSgLTmDS7w94VfogU57sYIgkFg4Qvv8Zq/prV2DYEFD4A86CEKC08LZj4h57bJme7tn9tmxlmaDfJ1nHl8iMCCdoFl7X/PO+4LafjXfpIki7zzHeGICG/yrnEj40HINPkIAS1rP/uYpLVP49ERCiz7+NDuDOby+8xrGWIr/6YIJFgL8P2TTftH5kFJZ5PxaBMr6G8PLrLTpx8Qfz7Na0WrKm0B6YNUwDJQ5R3zuRwrknOOOTMAMiBSeyzPhSrKAl/eBSpPYnIak9R+nfQl50ylkNPM+9edWGUIngUekpbxFTUxqPa5VUUPAIjq91XiIP28SPwA/OOiB0BGhieoiYifI7IGWgDZ2lNYNj1EVpoFZCX2FNXcrQEe4DVn2vvy4QgrkMnQYV5qJXfTBVpBxoegU+Hiycu1LGk/zlBB4ZSaaTYZf+gikKBdgNIFTRa/mmuNrX2xgRJ+2yy7JS3vQXyCgILvB/R3Br7mOgU/OZVudfxwcrTcQNmTj8OCc+eT81HVLllJ0MWQJ4XbLapBMZTjw/7Oq3Qj9PYkGT/gOqhwbQTWQmBXV5fz9fVnvmX1Sn7aTneGb3eHS7OEX03KvP4UgQUPgHf17XJaMQiVpEvp8+KldF1RAuCFCgKBDqTfv0Uk0d8LpCmtxWP4lyGrSLfEzUGSvK+UOutq7M2QBKIn211DIuojd+/AL5w4kcHuLGno7VCjr8bu+JQHXHduYO4D0YKZxa5tpZRSSimllFJKKe83zU4UhfQ1070AAAAASUVORK5CYII=",
    "dashboard": "data:image/png;base64,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",
    "deletion": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAACXBIWXMAACxLAAAsSwGlPZapAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAHFSURBVHgB7dq/TsJQFAbw79wS4+jo6EYwDPgGuGOsDNrVJ1CfgPAEyubIJLDwJ/AAuLmJCQm46RswG9tjq5sQ7rVpmtZ7fhvJbXr5uOeQNgcQQgghhK3IdGHN9aoOoQGiCsB7yCRagXnmM7Umw87Q5ArHZJFb9xpEaIdxHYQfd5Fdu9EeFcErlsp4XcwfdRdoT0DNPXcdpQbIIT/A8WTYnW5bo6DhkLpCTn2XrIY2gJ+azymDvRegtd7w/CA4K0DNkClBhddKVd+sDQJYt6MKz/3+wzsyxHU9xKEvgX9OAoDlJABYTgKA5SQAWE4CgOUkAFjO+gBiPQ5vclK/uFagW6QgAN2M+507JCCxE6CYTpESxZzYvaQHwHISABJCxCOkhJgSu1di/wLDfi/qyol05jRJCcByEgAsJwHAchIALCcBwHISACwnAcBysR6HPwI+cl3PeMo0DZ8IKk6M39MgAFr9nrZyFA8Y2bL5y0d7304fGXPGxuH+wGDv2gCI0URO+Ry0dGu0w9LL5fytVCpH9V5FjoQl2hwPeve6dUbT4svFfFoqHr6E52E/fPsZ9YOMToxH4/J4Ck/t5WjQbUMIIYQQYosvdKxjuvdNNYYAAAAASUVORK5CYII=",
    "files": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAACXBIWXMAACxLAAAsSwGlPZapAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAALnSURBVHgB7ZpPbtNAFMa/N+0iXZEjhBVCQiLcIN0jZRIkiLqBnqD0BG1PEHICygYVkNoRYp8coRKbLpMdO7KshDKPmZDwL05m7GScpJ6fFFmyx3be58/Pz54HRCKRIkMIjHx2cMRaS3OmGlYJ8zUTKaFvO0qpITISVIB6o9VdeeCz9EljX6mLPjIgEAjZbJ3kELylwgJdKVsVZCCIA6SUZRal78iXTE4I5IBSFfmTyQnBboFZaEh69MRcpfuev/3Eo9ht4OM5J0ktwi5yg4dKfbr2HW2CSFw/sfgbs31ogn2bMGQqgtftkKMDVosJ7ty44XDO5okIsgwHWyuAxSWCFqXXcLDVAlgWiWAecS9d+3vnAGunkdh7JcCPwagsGsvgcg5F5m+sCDZnJOSEimtfLwGkPKiy4K4YBwaP2PIL/i96yIBTAPtIscFjGvyaqTdbnLSekQ1nDjC2OtmU4EPgkQRJ4g7jkQNmrz4zd5hpblFDRFUiPsJS3JpX3L1haPdlqgR3aad9efV+MG+7yRs1JiwlgH3Hl/L5IQvRhkc2z0qOpXB6lPqo7MKzth9Xf0jJRgswxaemn/fu4GLrK8FliQKg4EQBUHCiACg4UQAUnCgACk4UAAUnCoCCEwVAwYkCoOAUXoA8P4pW6s0XV7ZTBAFgUDnLBFkoAfrJq0POMnGK//GHILfA+DM2sXc7TEB6rgHBcgCN6BjrxbbNnbkGBRPAuKBHWjfgYcOVY9zn2zMYNAnaqS0zY2NvhZomNhOmdM9vT5sr/p8UZeVKoCYLDIRGT6kPPXgS/CkwuQrnKXaxTRA1s/hHgJGmzhfjKqyYWAih4MRKEBn4AW48/ZXcAqBti105e9tTOjwEoJk2FQFuh/OOPXA+wU/PthjeiIquH+IJYHEKQCzWXdFZP7xDIHZcA25uvn57+ODRAIS1tMuZ4M8+X16cIhDePa22UUkTTsn2ChPl0DhJppzljgpk/UgkEokYfgLlZP9fGqRW9wAAAABJRU5ErkJggg==",
    "global-grey": "data:image/png;base64,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",
    "global": "data:image/png;base64,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",
    "insertion": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAACXBIWXMAACxLAAAsSwGlPZapAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAIUSURBVHgB7dqxThsxGAfw/+eLKsaOHbuhVAzpG6Q7FW4qtadufQLaJ0A8QWHryARh6OVSeAC6dQOkSIQN3oAZEX/4YEEJxCaxLnf4+y1RIkfn/GN/8TkGhBBCCBEr8m24qtN2QtgAUQvg16gkugLzyYhp+zDfy33ekfg00p10gwg7Nq639ukSqmup6KMipMvNFZyfDf653uAcAav6i06U6qGGRgYfDvPu0bQ2Cg4JqXXU1N2UdXAGcD/na8qj7w04TRa8kTGfGlAnqBTT4omp6i7WHgFMeqUax1m2e4kK0TrFLNxT4IWTABC5mWrAvPTnb+tsjH74mi1g+d8/u9so2UICYDZb40swYtO2D6UHIDUAkZMAEDkJAJGTABA5WQojkI+drz8U6BfmsNZJ2aedAf08yPa2EECwEaCY1lASxRzsWlIDEDkJAIEQcR8lIaZg1wr2K5Bn+0VV9qrMT1X7ftb1/qsuFJkCiJwEgMhJAIicBIDIyX4AFoDs/TyP3dISUWlL6YcWEkB+v5kRZENjXlIDEDkpgpjBteH3Wqel37pOcwPTSmb4Pj0CoKvx01aJ4p7X9m2JHv/wRd+nc0fGXLHjcM/g0XdnAMTYRE2N2DhPnDgPSw+Hg4tmc6WY723UiJ2imwe9/d+udl6nxYdng6Pm8rtTOx7e2CVbUQ8qemK8OC6P/3bUfu/3ujsQQgghhJjiFmCogK5st/Z6AAAAAElFTkSuQmCC",
    "message": "data:image/png;base64,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",
    "paw": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAACXBIWXMAACxLAAAsSwGlPZapAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAARXSURBVHgB7ZpPUhNBFMa/ngTUckHwX5Ur4wmMJzCsQU1OIJxAPAFyAvAEwRMEJFkTT0BuQFy5EEisssoykm67JwwmmemZftM9kNL5VVkCM2/69Tfdr1+/HiAnJycnJyfnf4XBJYffqvCKbyFEVf5Wkv8GYKyD0egArx7sGdmz4hYgKjP2H6X9PjLAnQCt/o50fFN7nYk9DL13qC8PIq+3+w0p3LrWHmIXa/ffwTEeXJDUeYVg61gUDa19bOcVbBOtswYcYz8C2qfrEJ65Y5xvTE0Hqr0YreDlww4cYT8CROEN6X7Pe2NlzwpbcIiDKeAHLArVGfsqaFDbi8VFDCiBSvvnE6SH3l4MLgQYgMrqnS8W9vT2YnAhQBc0Opb21PtjcRAER9uk+zn/6NTekuRlsHlSwuLdMjgbz72LH13Un04Pw8OzXZmxvU18lhAf8PJ+OF9one7Jd5G8GkTZz/pHXCL1AvgPLqm0VjU4HXj8rG64jfrj3tXfDs/eSxG2SM5PkiTirL3eP5k+i/2QfxqiBWh+LWPh1pH8qRxj28PvXytTjTT70o6/l499hvFy1ZPOdPxha/Jm/L2At55on9a/CKIFaJ2fJDx8ohH2XJvfZ4F68wtLx3DkXzgIqtTU7OHw7yvyTVwnatg79C8sADk1NQh+LkncNM3A2Iu4yxHLIDk1Lcm57zQ70zJupwwa1biLRbhg8fYSkjK0cYB7LTWvSZFVRy5FY10w3sVIHBgUPZwLHQ6C5gEwYIC1e8vaq37HCw2YBi3Ot2OrR63zPmhC9KR/T3UXI2KAoGVajOnfmip0sELScjVJWW6XG7LwsaO9g8uRQkGV1GIIC3Dh7YKy4RgiOpVVJa6kKpEWVf05P46MLYXRLswZaP27JCyAWjM5N6u9CSGzreVe6O+J9T0jKlgQRyERVh/JzZAw80/1I8q/CfSpcPzcHYsUNVfddH6SrkxmVkLJzLiUtqXxryc3WRsm2WfyZujTaU3OI1nuxhI4vsMTXQwL+5HZlfvOB0SL4LcpheCscuUf+D4uil3T7NRdWTy7zgfoRbDAjQDZdz7AuQgOyuLX1vkApyLYCXD9nQ9wJkJ6AW6u8wFOREhXEzQ6ysocmSfwHVhCHwHUo6ys4bxuc3JMHwHj5GN+8DyrUUATQCVF9P141pT9rDUlNAEK7DXmEa9Iq2JNmpLuFqyCuYRcxbqCGgPmUwCRflq6+UJkHkh54vzvCDB94mwMVYAe5pPU2SBNAC4+Yz5J7RdxBIjUGVemcJ7aL3oqTC9LZ01s2TsJehBk3PnHilaocwQL0m2H2+dNufbWcNOoM4nV5TosSLcMDtkG7L/VsbcfYgOWpBNAFSFUMQLEU6QAdZ6wdu+5/38a1Ju/8YpQQHx9fpaO/1HUZL2+3a9IIZqG9vrziJS4K4urrbLHahOftyjUG5KHFCp/kEtV3EGFv6X1apfn+WX8XWlon9nk5OTk5OTk5BjyB/2/21RCdE7tAAAAAElFTkSuQmCC",
    "readme": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAACXBIWXMAACxLAAAsSwGlPZapAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAInSURBVHgB7dpPTuMwFAbwz1HCCGk04ghdzmIYlRMQnwCOUE4A3KCcADgBcAM4QcINKpUFyx6BHYIWHn4IiT8qpemzTYrfb2PJihLna+zYdQCllFJKpcrAA6o6a5Psz64h9AjUgUeugSNX1GMaH6za6xE8EwfwfPPmd+VO1UVAHIQLwfoOIYMQ//Khb54R0ClMUd1WfzvwSByAIeohkhAhiLvAuF6nD1X1I9ElFpAZs+mK8qvjfHaHHJ7xzf+yV30s4K7613chlG/riLBjDE7e1b0+CeIQxF0gtBU7POUQPtb76g6tD4CFDGEpAmChQliaANhXIVDVXUNDSxUAmxXCPSZ7aGjpAmCfheDeILtoyPtr0Lcp84xZfn4X8K1VAbiV5A0ia1kAxbkroobQqjFg1Q5Gt1V3I8OkN8/x864dZmndIMghuKI/z7HT1g5N6SCIxGkASFyUQXB8+f/Q/WO8DQEydF5sDvfhWZy3ANFek/ns9HOAFzreA9AxAImLFUANMaoRQJQxoCiHFi2lXQCJizMPqNfd5qls1ebUIbpSrCeghFyJAHQMQOJiTYWPjTFbECCiCwQQZx5gr3ge33jTIgYdA5A4DQCJ0wCQOJ0IwTPeruIdG0TwsjUmIg6Av9njrzPeVJXS7SpJW9CQuAs8EJ2hJWiBtogDWEF+5LIf4NvRIH9uSzPyb4Xt4CanzLr4DxZ5BMXX52u6a+eUW24LlFJKKaXm9AQtHMD8AleU8gAAAABJRU5ErkJggg==",
    "rocket-grey": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAACXBIWXMAACxLAAAsSwGlPZapAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAANISURBVHgB7ZpdbhMxEMf/4/QAuUHTG5QT0L5Du0RCCn0hPUG5QdMTQE9A+oICEmUj8d4coZygyw36ViERD/YmqZC6Wdu73i/wT4rysY6T+Y/tGY8XCAQCgUAg8L9CaDkvotEBCdoXkM/V391Xjz7A/YymCVg9iO8Z9ENKLL7Hs4Wp/1YKoI0Wgo8JYrzFWCuWEocmEXbQIqJoNGDCR+WWg5VvGGUQQveDRW4btISj4eicBe5WxvtBSbhratP4CHj0OvwZ/gjrNSOfRgVIjRe4US8HqAIyrx+NTQF34+leDekLktibX89IP+v3+vOcLw2MvaIBChkv6TCOP90+7etknwXfbIsWWqycjpsZAa7DnsGXWcZr9OekrqMgtQtwNHzzHo5zXkhMcxuYruf1jRp5GY3Gylvv4Egcz5Iy1/OoTQA971Vico4CDIcnu6a+s6/kLpAphcOgTld7pAyyTFzK5HS/IU/V02Rrg544Bktk/GgCA4VGQKSytp5eyKiC5CUDAp1F0evMpCaNAsyTrGsM+RMGnEdAGsLyvFEJ3Gexc6PS5Q9qQbzSc17/DynwltM1ZUvCQ3Rr6tlZAC44j8vDfRXQJ+r3J8fDUTqlVgF+++TSW2IYcEqE1gnMHbpBopKgPVMjpzWgOe8XYmHTyFqAdagZoyOovcKFTTtrATrm/altcmQlwL/qfY1VFOiS91VMuJg7pMbGKNCplZ/4dv718zOXrxinQIe8n9CSXsERmzVgjPaTqHl/WGRXaBZADSu0m8LGa4wC0LKnd2IJ2ohyThnj0y7giboXS7UDvBT8axLHsXHPn4e3srgUdEYlT3Ls0AXS5ek8/hLDA14EWG2ROUINkHzYK+v1v/FSEluK1PgBasCn8RovApDFEVRb8SKA4LRClKCDeBFAhyEdjtBBEbyVxbsqgtdzgS6K4P1gxCwCeV3Fy1LJyVC2CJvj7QdjobJOKjsa24igU9aN4fH1bOI7jpel0jtE1psU58PQOmnNTVJWsF2p24VOCUCEK3imVfcJ5pEWO69nU3imCwJMdZl7XqLokUebBUgNjysyfEMbBajF8A3NCKALrU+30LUavqERAXShlYX8hlURpRHDA4FAIBAIBP4A/SBJr7a8vKQAAAAASUVORK5CYII=",
    "rocket": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAACXBIWXMAACxLAAAsSwGlPZapAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAANfSURBVHgB7ZpdTttAEMdnTFIqVBA5AQ4nSE/QcALoCUoeS1RBT0A4AaAK8lIJOEF7A3KE9ATZnqBRg0Q/kp3OGiKBcLxeZ2N7y/4eINHaq8x/1zM7MwbweDwej8fzXEEoOeGnURNQNoIgeENADSBc51+9/vRKEoAokGAoSX4DGfTEh9Webv5SChAZXcVtnNBuvLHpoAls6USoQIkIj3+EuFy54I9NkDT/8gSyyX97iZdASdjsjg7Z+AEo4y0RBEsbumsK3wHTVSeyZ/gUIvYZGgoV4M746jX/1BAWAmr9R2GPgLHxREPeJUeElfpgbxUJx3X1HdjrJ9wU6qYtJApkMh4mW6Jd6z+Z6+ymgUDXs6KFEith5mJ2gOm2J8DTOOMVov2qTyBPISO5C7B5Pjo2fuaD8WXyuEweT7oVciQ8+7nL0f0ADBHva2Ke8SRyEyB67jE4hAzUP99u6OaeMZTgIO/IHAbVcRWXQBnUTH8XQRbo958W/+vMGg9eVLcpfm4BGjLtgOjUtgTsyOwfXuLgnbOvvH3cGK9+g43vxI0R0nfQYLwD1Hbj+NuBfFlHpGsW/kT+Gl+JjzURdm/DAMbvSLJPmZUwSerrJjY+B4TdmwskztIcIE02aCTA/bl9AE5AYrC3VtddZeYDXlYzefEiYL/RS3NdagGi1Xdk6ysk/D1Kc136HeDU6uNl2sNRKgH+19VXpNsBDq2+SpFNjsbaKOCW54c+p7+vTW7Q7wBnVp8EF0negiFaAdx49pXxXDDJkBWm8QHa42SxZDdeoRWACFtR16Wc9OcxXmGtJpi3s2Rvfwor445o1bQ5fxLWyuLBcnWfMub7RqgCKUJLtNe+ggWsCBClyAA7kAO0MqnPu+oPsVMSWw52FtfceIxN4xW2aoLaFlRZsSMAyk6JI0UiVgRQYUiFIxdFsFYWd1UEq30BF0Ww3hjRisBxHErEQjpDsSJM29scx6FELLQ9HnZVy6pywCWaIR9bT6YxvH4+ynxk1LW7TVnoGyL3SYpxMzRPSvOSVBo4B+iBZZwSgFtdV2AZZwSIip3ttUuwTOkFUDV+9UKUaK92YAGU6k3RhyjDVX1/MEe1Jw2lEyAvw6cUJYAqtD5KofM2fEohAqhCK6L8wmaHRRnu8Xg8Ho/H8w9+l22pYfGvRwAAAABJRU5ErkJggg==",
    "visible": "data:image/png;base64,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"
}

# payload trigger to store it for later.
def post_json(json_data):
    # save the data to the offline data file
    storePayload(json_data)

    PluginData.reset_source_data()

#
# Background thread used to send data every minute.
#
class BackgroundWorker():
    def __init__(self, threads_count, target_func):
        self.queue = Queue(maxsize=0)
        self.target_func = target_func
        self.threads = []

        for i in range(threads_count):
            thread = Thread(target=self.worker, daemon=True)
            thread.start()
            self.threads.append(thread)

    def worker(self):
        while True:
            self.target_func(self.queue.get())
            self.queue.task_done()

#
# kpm payload data structure
#
class PluginData():
    __slots__ = ('source', 'keystrokes', 'start', 'local_start', 'project', 'pluginId', 'version', 'os', 'timezone')
    background_worker = BackgroundWorker(1, post_json)
    active_datas = {}
    line_counts = {}
    send_timer = None

    def __init__(self, project):
        self.source = {}
        self.start = 0
        self.local_start = 0
        self.timezone = ''
        self.keystrokes = 0
        self.project = project
        self.pluginId = PLUGIN_ID
        self.version = VERSION
        self.timezone = getTimezone()
        self.os = getOs()

    def json(self):

        # make sure all file end times are set

        dict_data = {key: getattr(self, key, None)
                     for key in self.__slots__}

        return json.dumps(dict_data)

    # send the kpm info
    def send(self):
        # check if it has data
        if PluginData.background_worker and self.hasData():
            PluginData.endUnendedFileEndTimes()
            PluginData.background_worker.queue.put(self.json())

    # check if we have data
    def hasData(self):
        if (self.keystrokes > 0):
            return True
        for fileName in self.source:
            fileInfo = self.source[fileName]
            if (fileInfo['close'] > 0 or
                fileInfo['open'] > 0 or
                fileInfo['paste'] > 0 or
                fileInfo['delete'] > 0 or
                fileInfo['add'] > 0 or
                fileInfo['netkeys'] > 0):
                return True
        return False

    @staticmethod
    def reset_source_data():
        PluginData.send_timer = None

        for dir in PluginData.active_datas:
            keystrokeCountObj = PluginData.active_datas[dir]
            
            # get the lines so we can add that back
            for fileName in keystrokeCountObj.source:
                fileInfo = keystrokeCountObj.source[fileName]
                # add the lines for this file so we can re-use again
                PluginData.line_counts[fileName] = fileInfo.get("lines", 0)

            if keystrokeCountObj is not None:
                keystrokeCountObj.source = {}
                keystrokeCountObj.keystrokes = 0
                keystrokeCountObj.project['identifier'] = None
                keystrokeCountObj.timezone = getTimezone()

    @staticmethod
    def create_empty_payload(fileName, projectName):
        project = {}
        project['directory'] = projectName
        project['name'] = projectName
        return_data = PluginData(project)
        PluginData.active_datas[project['directory']] = return_data
        PluginData.get_file_info_and_initialize_if_none(return_data, fileName)
        return return_data

    @staticmethod
    def get_active_data(view):
        return_data = None
        if view is None or view.window() is None:
            return return_data

        fileName = view.file_name()
        if (fileName is None):
            fileName = "Untitled"

        sublime_variables = view.window().extract_variables()
        project = {}

        # set it to none as a default
        projectFolder = 'Unnamed'

        # set the project folder
        if 'folder' in sublime_variables:
            projectFolder = sublime_variables['folder']
        elif 'file_path' in sublime_variables:
            projectFolder = sublime_variables['file_path']

        # if we have a valid project folder, set the project name from it
        if projectFolder != 'Unnamed':
            project['directory'] = projectFolder
            if 'project_name' in sublime_variables:
                project['name'] = sublime_variables['project_name']
            else:
                # use last file name in the folder as the project name
                projectNameIdx = projectFolder.rfind('/')
                if projectNameIdx > -1:
                    projectName = projectFolder[projectNameIdx + 1:]
                    project['name'] = projectName
        else:
            project['directory'] = 'Unnamed'

        old_active_data = None
        if project['directory'] in PluginData.active_datas:
            old_active_data = PluginData.active_datas[project['directory']]
        
        if old_active_data is None:
            new_active_data = PluginData(project)

            PluginData.active_datas[project['directory']] = new_active_data
            return_data = new_active_data
        else:
            return_data = old_active_data

        fileInfoData = PluginData.get_file_info_and_initialize_if_none(return_data, fileName)

        # This activates the 60 second timer. The callback
        # in the Timer sends the data
        if (PluginData.send_timer is None):
            PluginData.send_timer = Timer(DEFAULT_DURATION, return_data.send)
            PluginData.send_timer.start()

        return return_data

    # ...
    @staticmethod
    def get_existing_file_info(fileName):
        fileInfoData = None

        now = round(time.time())
        local_start = getLocalStart()
        # Get the FileInfo object within the KeystrokesCount object
        # based on the specified fileName.
        for dir in PluginData.active_datas:
            keystrokeCountObj = PluginData.active_datas[dir]
            if keystrokeCountObj is not None:
                hasExistingKeystrokeObj = True
                # we have a keystroke count object, get the fileInfo
                if keystrokeCountObj.source is not None and fileName in keystrokeCountObj.source:
                    # set the fileInfoData we'll return the calling def
                    fileInfoData = keystrokeCountObj.source[fileName]
                else:
                    # end the other files end times
                    for fileName in keystrokeCountObj.source:
                        fileInfo = keystrokeCountObj.source[fileName]
                        fileInfo["end"] = now
                        fileInfo["local_end"] = local_start

        return fileInfoData

    # 
    @staticmethod
    def endUnendedFileEndTimes():
        now = round(time.time())
        local_start = getLocalStart()
        
        for dir in PluginData.active_datas:
            keystrokeCountObj = PluginData.active_datas[dir]
            if keystrokeCountObj is not None and keystrokeCountObj.source is not None:
                for fileName in keystrokeCountObj.source:
                    fileInfo = keystrokeCountObj.source[fileName]
                    if (fileInfo.get("end", 0) == 0):
                        fileInfo["end"] = now
                        fileInfo["local_end"] = local_start

    @staticmethod
    def send_all_datas():
        for dir in PluginData.active_datas:
            PluginData.active_datas[dir].send()

    #.........
    @staticmethod
    def initialize_file_info(keystrokeCount, fileName):
        if keystrokeCount is None:
            return

        if fileName is None or fileName == '':
            fileName = 'Untitled'
        
        # create the new FileInfo, which will contain a dictionary
        # of fileName and it's metrics
        fileInfoData = PluginData.get_existing_file_info(fileName)

        now = round(time.time())
        local_start = getLocalStart()

        if keystrokeCount.start == 0:
            keystrokeCount.start = now
            keystrokeCount.local_start = local_start
            keystrokeCount.timezone = getTimezone()

        # "add" = additive keystrokes
        # "netkeys" = add - delete
        # "keys" = add + delete
        # "delete" = delete keystrokes
        if fileInfoData is None:
            fileInfoData = {}
            fileInfoData['paste'] = 0
            fileInfoData['open'] = 0
            fileInfoData['close'] = 0
            fileInfoData['length'] = 0
            fileInfoData['delete'] = 0
            fileInfoData['netkeys'] = 0
            fileInfoData['add'] = 0
            fileInfoData['lines'] = -1
            fileInfoData['linesAdded'] = 0
            fileInfoData['linesRemoved'] = 0
            fileInfoData['syntax'] = ""
            fileInfoData['start'] = now
            fileInfoData['local_start'] = local_start
            fileInfoData['end'] = 0
            fileInfoData['local_end'] = 0
            keystrokeCount.source[fileName] = fileInfoData
        else:
            # update the end and local_end to zero since the file is still getting modified
            fileInfoData['end'] = 0
            fileInfoData['local_end'] = 0

    @staticmethod
    def get_file_info_and_initialize_if_none(keystrokeCount, fileName):
        fileInfoData = PluginData.get_existing_file_info(fileName)
        if fileInfoData is None:
            PluginData.initialize_file_info(keystrokeCount, fileName)
            fileInfoData = PluginData.get_existing_file_info(fileName)

        return fileInfoData

    @staticmethod
    def send_initial_payload():
        fileName = "Untitled"
        active_data = PluginData.create_empty_payload(fileName, "Unnamed")
        PluginData.get_file_info_and_initialize_if_none(active_data, fileName)
        fileInfoData = PluginData.get_existing_file_info(fileName)
        fileInfoData['add'] = 1
        active_data.keystrokes = 1
        PluginData.send_all_datas()

class GoToSoftware(sublime_plugin.TextCommand):
    def run(self, edit):
        launchWebDashboardUrl()

    def is_enabled(self):
        return (getValue("logged_on", True) is True)

# code_time_login command
class CodeTimeLogin(sublime_plugin.TextCommand):
    def run(self, edit):
        launchLoginUrl()

    def is_enabled(self):
        return (getValue("logged_on", True) is False)

# Command to launch the code time metrics "launch_code_time_metrics"
class LaunchCodeTimeMetrics(sublime_plugin.TextCommand):
    def run(self, edit):
        launchCodeTimeMetrics()

class LaunchCustomDashboard(sublime_plugin.WindowCommand):
    def run(self):
        d = datetime.datetime.now()
        current_time = d.strftime("%m/%d/%Y")
        t = d - datetime.timedelta(days=7)
        time_ago = t.strftime("%m/%d/%Y")
        # default range: last 7 days
        default_range = str(time_ago) + ", " + str(current_time)
        self.window.show_input_panel("Enter a start and end date (format: MM/DD/YYYY):", default_range, self.on_done, None, None)

    def on_done(self, result):
        setValue("date_range", result)
        launchCustomDashboard()

# connect spotify menu
class ConnectSpotify(sublime_plugin.TextCommand):
    def run(self, edit):
        launchSpotifyLoginUrl()

    # def is_enabled(self):
    #     loggedOn = getValue("logged_on", True)
    #     online = getValue("online", True)
    #     if (loggedOn is False and online is True):
    #         return True
    #     else:
    #         return False


class SoftwareTopForty(sublime_plugin.TextCommand):
    def run(self, edit):
        webbrowser.open("https://api.software.com/music/top40")

    def is_enabled(self):
        return (getValue("online", True) is True)

class OpenTreeView(sublime_plugin.TextCommand):

    def run(self, edit):
        tree_view = None
        window = self.view.window()
        orig_view = window.active_view()
        if not tree_view:
            window.set_sidebar_visible(False)
            layout = window.get_layout()
            if len(layout['cols']) < 3:
                layout['cols'] = [0, 0.2, 1]
                layout['cells'] = [[0, 0, 1, len(layout['rows']) - 1]] + [
                    [cell[0] + 1, cell[1], cell[2] + 1, cell[3]] for cell in layout['cells']
                ]
                window.set_layout(layout)
                for view in window.views():
                    (group, index) = window.get_view_index(view)
                    window.set_view_index(view, group + 1, index)
            elif layout['cols'][1] > 0.3:
                layout['cols'] = [0, min(0.2, layout['cols'][1] / 2.0)] + layout['cols'][1:]
                layout['cells'] = [[0, 0, 1, len(layout['rows']) - 1]] + [
                    [cell[0] + 1, cell[1], cell[2] + 1, cell[3]] for cell in layout['cells']
                ]
                window.set_layout(layout)
                for view in window.views():
                    (group, index) = window.get_view_index(view)
                    window.set_view_index(view, group + 1, index)

            tree_view = window.new_file()
            tree_view.settings().set('line_numbers', False)
            tree_view.settings().set('gutter', False)
            tree_view.settings().set('rulers', [])
            tree_view.set_read_only(True)
            tree_view.set_name('Code Time Tree View')
            tree_view.set_scratch(True)
            if window.num_groups() > 1: 
                (group, index) = window.get_view_index(orig_view)
                if group != 0:
                    group = 0
                    window.set_view_index(tree_view, group, 0)
                    window.focus_view(orig_view) # Um... Seems like a bug
        else:
        	tree_view.erase_phantoms('remote_tree')

        self.view = tree_view
        self.phantom_set = sublime.PhantomSet(tree_view, 'remote_tree')

        # trees.append(self) 

        self.tree = { 
        	'index': 0,
        	'depth': 0,
        	'path': '',
        	'name': '',
        	'dir': True,
        	'expanded': False,
        	'childs': [
                {
                    'index': 1,
                    'depth': 1,
                    'name': 'CODE TIME',
                    'dir': True,
                    'expanded': False,
                    'childs': [
                        {
                            'index': 2,
                            'depth': 2,
                            'icon': 'paw',
                            'name': 'See advanced metrics',
                            'dir': False,
                            'expanded': False,
                            'childs': None
                        },
                        {
                            'index': 3,
                            'depth': 2,
                            'icon': 'dashboard',
                            'name': 'Generate dashboard',
                            'dir': False,
                            'expanded': False,
                            'childs': None
                        },
                        {
                            'index': 4,
                            'depth': 2,
                            'icon': 'visible',
                            'name': 'Hide status bar metrics', #TODO: make this a switch with Show status bar metrics
                            'dir': False,
                            'expanded': False,
                            'childs': None
                        },
                        {
                            'index': 5,
                            'depth': 2,
                            'icon': 'readme',
                            'name': 'Learn more',
                            'dir': False,
                            'expanded': False,
                            'childs': None
                        },
                        {
                            'index': 6,
                            'depth': 2,
                            'icon': 'message',
                            'name': 'Submit feedback',
                            'dir': False,
                            'expanded': False,
                            'childs': None
                        }
                    ]
                },
                {
                    'index': 7,
                    'depth': 1,
                    'name': 'ACTIVITY METRICS',
                    'dir': True,
                    'expanded': False,
                    'childs': [
                        {
                            'index': 8,
                            'depth': 2,
                            'name': 'Editor time',
                            'dir': True,
                            'expanded': False,
                            'childs': [
                                {
                                    'index': 9,
                                    'depth': 3,
                                    'name': 'Today: 0 min', #TODO: hardcoded right now
                                    'dir': False,
                                    'expanded': False,
                                    'childs': None
                                }
                            ]
                        },
                        {
                            'index': 9,
                            'depth': 2,
                            'name': 'Code time',
                            'dir': True,
                            'expanded': False,
                            'childs': [
                                {
                                    'index': 10,
                                    'depth': 3,
                                    'name': 'Today: 0 min', #TODO: hardcoded right now
                                    'dir': False,
                                    'expanded': False,
                                    'childs': None
                                },
                                {
                                    'index': 11,
                                    'depth': 3,
                                    'name': 'Your average: 0 min', #TODO: hardcoded right now
                                    'dir': False,
                                    'expanded': False,
                                    'childs': None
                                },
                                {
                                    'index': 12,
                                    'depth': 3,
                                    'name': 'Global average: 0 min', #TODO: hardcoded right now
                                    'dir': False,
                                    'expanded': False,
                                    'childs': None
                                }
                            ]
                        },
                        {
                            'index': 13,
                            'depth': 2,
                            'name': 'Lines added',
                            'dir': True,
                            'expanded': False,
                            'childs': [
                                {
                                    'index': 14,
                                    'depth': 3,
                                    'name': 'Today: 0 min', #TODO: hardcoded right now
                                    'dir': False,
                                    'expanded': False,
                                    'childs': None
                                },
                                {
                                    'index': 15,
                                    'depth': 3,
                                    'name': 'Your average: 0 min', #TODO: hardcoded right now
                                    'dir': False,
                                    'expanded': False,
                                    'childs': None
                                },
                                {
                                    'index': 16,
                                    'depth': 3,
                                    'name': 'Global average: 0 min', #TODO: hardcoded right now
                                    'dir': False,
                                    'expanded': False,
                                    'childs': None
                                }
                            ]
                        },
                            {
                            'index': 17,
                            'depth': 2,
                            'name': 'Lines removed',
                            'dir': True,
                            'expanded': False,
                            'childs': [
                                {
                                    'index': 18,
                                    'depth': 3,
                                    'name': 'Today: 0 min', #TODO: hardcoded right now
                                    'dir': False,
                                    'expanded': False,
                                    'childs': None
                                },
                                {
                                    'index': 19,
                                    'depth': 3,
                                    'name': 'Your average: 0 min', #TODO: hardcoded right now
                                    'dir': False,
                                    'expanded': False,
                                    'childs': None
                                },
                                {
                                    'index': 20,
                                    'depth': 3,
                                    'name': 'Global average: 0 min', #TODO: hardcoded right now
                                    'dir': False,
                                    'expanded': False,
                                    'childs': None
                                }
                            ]
                        }
                    ]
                },
                {
                    'index': 21,
                    'depth': 1,
                    'name': 'PROJECT METRICS',
                    'dir': True,
                    'expanded': False,
                    'childs': [
                        {
                            'index': 22,
                            'depth': 2,
                            'name': 'Open changes',
                            'dir': True,
                            'expanded': False,
                            'childs': None
                        },
                        {
                            'index': 23,
                            'depth': 2,
                            'name': 'Committed today',
                            'dir': True,
                            'expanded': False,
                            'childs': None
                        }
                    ]
                }
                
            ]
        }
        self.list = [self.tree]
        self.opened = None
        self.expand(0)


    def expand(self, index):
        item = self.list[index]
        item['expanded'] = not item['expanded']
        if item['expanded']: # and item['childs'] == None -- caching
            if item['childs']:
                for child in item['childs']:
                    child['index'] = len(self.list)
                    self.list.append(child)
            self.rebuild_phantom()
        else:
            self.rebuild_phantom()

    def open(self, index):  
        item = self.list[index]
        self.opened = item
        self.rebuild_phantom()

    def on_click(self, url):
        comps = url.split('/')
        if comps[0] == 'open':
            self.open(int(comps[1]))
        else:
            self.expand(int(comps[1]))

    def rebuild_phantom(self):
        result = self.render_subtree(self.tree, [])
        # print(result)
        html = '''<body id="tree">
            <style>
            body {
            font-size: 12px;
            line-height: 16px;
            }
            .file a, .dir a {
            display: block;
            padding-left: 4px;
            }
            .dir a {
            padding-top: 1px;
            padding-bottom: 2px;
            text-decoration: none;
            }
            .file.active {
            background-color: color(var(--background) blend(var(--foreground) 80%));
            border-radius: 3px;
            }
            .file span {
            font-size: 7px; 
            }
            .file a {
            text-decoration: none;
            padding-bottom: 5px;
            color: var(--foreground);
            }
        </style>''' + ''.join(result) + '</body>'
        self.phantom = sublime.Phantom(sublime.Region(0), html, sublime.LAYOUT_BLOCK, on_navigate=self.on_click)
        self.phantom_set.update([self.phantom])


    # TODO: modify render_subtree
    def render_subtree(self, item, result):
        # if file
        # if not item['dir']:
        #     result.append('<div class="file{active}" style="margin-left: {margin}px"><a href=open/{index}><span>📄&nbsp;</span>{name}</a></div>'.format(
        #         active=' active' if item == self.opened else '',
        #         margin=(item['depth'] * 20) - 10,
        #         index=item['index'],
        #         name=item['name']))
        #     return result
        
        if not item['dir']:
            if 'icon' in item:
                result.append('<div class="file{active}" style="margin-left: {margin}px;"><a href=open/{index}><img height="16" width="16" alt="" src="{icon}">{name}</a></div>'.format(
                    active=' active' if item == self.opened else '',
                    margin=(item['depth'] * 20) - 10,
                    index=item['index'],
                    name=item['name'],
                    icon=icons[item['icon']]))
                return result
            else:
                result.append('<div class="file{active}" style="margin-left: {margin}px"><a href=open/{index}><span>📄&nbsp;</span>{name}</a></div>'.format(
                    active=' active' if item == self.opened else '',
                    margin=(item['depth'] * 20) - 10,
                    index=item['index'],
                    name=item['name']))
                return result


        # if in a directory
        if item['depth'] > 0:
            result.append('<div class="dir" style="margin-left: {margin}px"><a href=expand/{index}>{sign}&nbsp;{name}</a></div>'.format(
                margin=(item['depth'] * 20) - 10,
                index=item['index'],
                name=item['name'],
                sign='▼' if item['expanded'] else '▶'))

        # if directory with things
        if item['childs'] != None and item['expanded']:
            for child in item['childs']:
                self.render_subtree(child, result)

        return result


class ToggleStatusBarMetrics(sublime_plugin.TextCommand):
    def run(self, edit):
        log("toggling status bar metrics")

        showStatusVal = getValue("show_code_time_status", True)
        if (showStatusVal):
            setValue("show_code_time_status", False)
        else:
            setValue("show_code_time_status", True)

        toggleStatus()

# Mute Console message
class HideConsoleMessage(sublime_plugin.TextCommand):
    def run(self, edit):
        log("Code Time: Console Messages Disabled !")
        # showStatus("Paused")
        setValue("software_logging_on", False)

    def is_enabled(self):
        return (getValue("software_logging_on", True) is True)

# Command to re-enable Console message
class ShowConsoleMessage(sublime_plugin.TextCommand):
    def run(self, edit):
        log("Code Time: Console Messages Enabled !")
        # showStatus("Code Time")
        setValue("software_logging_on", True)

    def is_enabled(self):
        return (getValue("software_logging_on", True) is False)
    
# Command to pause kpm metrics
class PauseKpmUpdatesCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        log("software kpm metrics paused")
        showStatus("Paused")
        setValue("software_telemetry_on", False)

    def is_enabled(self):
        return (getValue("software_telemetry_on", True) is True)

# Command to re-enable kpm metrics
class EnableKpmUpdatesCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        log("software kpm metrics enabled")
        showStatus("Code Time")
        setValue("software_telemetry_on", True)

    def is_enabled(self):
        return (getValue("software_telemetry_on", True) is False)

# Runs once instance per view (i.e. tab, or single file window)
class EventListener(sublime_plugin.EventListener):
    def on_load_async(self, view):
        fileName = view.file_name()
        if (fileName is None):
            fileName = "Untitled"

        active_data = PluginData.get_active_data(view)

        # get the file info to increment the open metric
        fileInfoData = PluginData.get_file_info_and_initialize_if_none(active_data, fileName)
        if fileInfoData is None:
            return

        fileSize = view.size()
        fileInfoData['length'] = fileSize

        # get the number of lines
        lines = view.rowcol(fileSize)[0] + 1
        fileInfoData['lines'] = lines

        # we have the fileinfo, update the metric
        fileInfoData['open'] += 1
        log('Code Time: opened file %s' % fileName)

        # show last status message
        redispayStatus() 

    def on_close(self, view):
        fileName = view.file_name()
        if (fileName is None):
            fileName = "Untitled"

        active_data = PluginData.get_active_data(view)

        # get the file info to increment the close metric
        fileInfoData = PluginData.get_file_info_and_initialize_if_none(active_data, fileName)
        if fileInfoData is None:
            return

        fileSize = view.size()
        fileInfoData['length'] = fileSize

        # get the number of lines
        lines = view.rowcol(fileSize)[0] + 1
        fileInfoData['lines'] = lines

        # we have the fileInfo, update the metric
        fileInfoData['close'] += 1
        log('Code Time: closed file %s' % fileName)
        
        # show last status message
        redispayStatus() 

    def on_modified_async(self, view):
        global PROJECT_DIR
        # get active data will create the file info if it doesn't exist
        active_data = PluginData.get_active_data(view)
        if active_data is None:
            return

        # add the count for the file
        fileName = view.file_name()
        
        fileInfoData = {}
        
        if (fileName is None):
            fileName = "Untitled"
            
        fileInfoData = PluginData.get_file_info_and_initialize_if_none(active_data, fileName)
        
        # If file is untitled then log that msg and set file open metrics to 1
        if fileName == "Untitled":
            log("Code Time: opened file untitled")
            fileInfoData['open'] = 1
        else:
            pass

        if fileInfoData is None:
            return

        fileSize = view.size()

        #lines = 0
        # rowcol gives 0-based line number, need to add one as on editor lines starts from 1 
        lines = view.rowcol(fileSize)[0] + 1
        
        prevLines = fileInfoData['lines']
        if (prevLines == 0):

            if (PluginData.line_counts.get(fileName) is None):
                PluginData.line_counts[fileName] = prevLines

            prevLines = PluginData.line_counts[fileName]
        elif (prevLines > 0):
            fileInfoData['lines'] = prevLines

        lineDiff = 0
        if (prevLines > 0):
            lineDiff = lines - prevLines
            if (lineDiff > 0):
                fileInfoData['linesAdded'] += lineDiff
                log('Code Time: linesAdded incremented')
            elif (lineDiff < 0):
                fileInfoData['linesRemoved'] += abs(lineDiff)
                log('Code Time: linesRemoved incremented')

        fileInfoData['lines'] = lines
        
        # subtract the current size of the file from what we had before
        # we'll know whether it's a delete, copy+paste, or kpm.
        currLen = fileInfoData['length']

        charCountDiff = 0
        
        if currLen > 0 or currLen == 0:
        # currLen > 0 only worked for existing file, currlen==0 will work for new file
            charCountDiff = fileSize - currLen

        if (not fileInfoData["syntax"]):
            syntax = view.settings().get('syntax')
            # get the last occurance of the "/" then get the 1st occurance of the .sublime-syntax
            # [language].sublime-syntax
            # Packages/Python/Python.sublime-syntax
            syntax = syntax[syntax.rfind('/') + 1:-len(".sublime-syntax")]
            if (syntax):
                fileInfoData["syntax"] = syntax

        PROJECT_DIR = active_data.project['directory']

        # getResourceInfo is a SoftwareUtil function
        if (active_data.project.get("identifier") is None):
            resourceInfoDict = getResourceInfo(PROJECT_DIR)
            if (resourceInfoDict.get("identifier") is not None):
                active_data.project['identifier'] = resourceInfoDict['identifier']
                active_data.project['resource'] = resourceInfoDict

        
        fileInfoData['length'] = fileSize

        if lineDiff == 0 and charCountDiff > 8:
            fileInfoData['paste'] += 1
            log('Code Time: pasted incremented')
        elif lineDiff == 0 and charCountDiff == -1:
            fileInfoData['delete'] += 1
            log('Code Time: delete incremented')
        elif lineDiff == 0 and charCountDiff == 1:
            fileInfoData['add'] += 1
            log('Code Time: KPM incremented')

        # increment the overall count
        if (charCountDiff != 0 or lineDiff != 0):
            active_data.keystrokes += 1

        # update the netkeys and the keys
        # "netkeys" = add - delete
        fileInfoData['netkeys'] = fileInfoData['add'] - fileInfoData['delete']

#
# Iniates the plugin tasks once the it's loaded into Sublime.
#
def plugin_loaded():
    initializeUser()

def initializeUser():
    # check if the session file is there
    serverAvailable = checkOnline()
    fileExists = softwareSessionFileExists()
    jwt = getItem("jwt")
    log("JWT VAL: %s" % jwt)
    if (fileExists is False or jwt is None):
        if (serverAvailable is False):
            if (retry_counter == 0):
                showOfflinePrompt()
            initializeUserTimer = Timer(check_online_interval_sec, initializeUser)
            initializeUserTimer.start()
        else:
            result = createAnonymousUser(serverAvailable)
            if (result is None):
                if (retry_counter == 0):
                    showOfflinePrompt()
                initializeUserTimer = Timer(check_online_interval_sec, initializeUser)
                initializeUserTimer.start()
            else:
                initializePlugin(True, serverAvailable)
    else:
        initializePlugin(False, serverAvailable)

def initializePlugin(initializedAnonUser, serverAvailable):
    PACKAGE_NAME = __name__.split('.')[0]
    log('Code Time: Loaded v%s of package name: %s' % (VERSION, PACKAGE_NAME))
    showStatus("Code Time")

    setItem("sublime_lastUpdateTime", None)

    # fire off timer tasks (seconds, task)

    setOnlineStatusTimer = Timer(2, setOnlineStatus)
    setOnlineStatusTimer.start()

    sendOfflineDataTimer = Timer(10, sendOfflineData)
    sendOfflineDataTimer.start()

    gatherMusicTimer = Timer(45, gatherMusicInfo)
    gatherMusicTimer.start()

    hourlyTimer = Timer(60, hourlyTimerHandler)
    hourlyTimer.start()

    updateOnlineStatusTimer = Timer(0.25, updateOnlineStatus)
    updateOnlineStatusTimer.start()
    print("Online status timer initialized")

    initializeUserInfo(initializedAnonUser)

def initializeUserInfo(initializedAnonUser):
    getUserStatus()

    if (initializedAnonUser is True):
        showLoginPrompt()
        PluginData.send_initial_payload()

    sendInitHeartbeatTimer = Timer(15, sendInitializedHeartbeat)
    sendInitHeartbeatTimer.start()

    # re-fetch user info in another 90 seconds
    checkUserAuthTimer = Timer(90, userStatusHandler)
    checkUserAuthTimer.start()

def userStatusHandler():
    getUserStatus()

    loggedOn = getValue("logged_on", True)
    if (loggedOn is True):
        # no need to fetch any longer
        return
    
    # re-fetch user info in another 10 minutes
    checkUserAuthTimer = Timer(60 * 10, userStatusHandler)
    checkUserAuthTimer.start()

def plugin_unloaded():
    # clean up the background worker
    PluginData.background_worker.queue.join()

def sendInitializedHeartbeat():
    sendHeartbeat("INITIALIZED")

# gather the git commits, repo members, heatbeat ping
def hourlyTimerHandler():
    sendHeartbeat("HOURLY")

    # process commits in a minute
    processCommitsTimer = Timer(60, processCommits)
    processCommitsTimer.start()

    # run the handler in another hour
    hourlyTimer = Timer(60 * 60, hourlyTimerHandler)
    hourlyTimer.start()

# ...
def processCommits():
    global PROJECT_DIR
    gatherCommits(PROJECT_DIR)

def showOfflinePrompt():
    infoMsg = "Our service is temporarily unavailable. We will try to reconnect again in 10 minutes. Your status bar will not update at this time."
    sublime.message_dialog(infoMsg)

def setOnlineStatus():
    online = checkOnline()
    log("Code Time: Checking online status...")
    if (online is True):
        setValue("online", True)
        log("Code Time: Online")
    else:
        setValue("online", False)
        log("Code Time: Offline")

    # run the check in another 1 minute
    timer = Timer(60 * 1, setOnlineStatus)
    timer.start()


