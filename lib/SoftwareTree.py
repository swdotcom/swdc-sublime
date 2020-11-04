import sublime_plugin, sublime 
from copy import deepcopy
from threading import Thread, Timer, Event 
from .SoftwareOffline import getSessionSummaryData
from .SoftwareDashboard import launchCodeTimeMetrics
from .SoftwareUtil import *
from .SoftwareModels import SessionSummary
from .SoftwareHttp import *
from .SoftwareWallClock import *
from .SoftwareFileChangeInfoSummaryData import *
from .SoftwareRepo import *
from .SoftwareUserStatus import *
from .TimeSummaryData import *
from .CommonUtil import *
from .ui_interactions import UI_INTERACTIONS

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
    "visible": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAACXBIWXMAACxLAAAsSwGlPZapAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAWwSURBVHgB7ZprVttGFMfvHRFTHm3JCqquoM4KIjsLAD4CpYEVBFaAWQFmBYZDgY+QBcSoK4CuoOoK4jYQDsaa6R3JNrKsx4wk99gn+p2TQ7Cl0cxfd+5rACgpKSkpKSkpKSkp+RZBKIB3Fw9rgouW9wtjh+3NxSbMCLkFqF8+HACHRvAzDuKNvbV8BzMAg7yEFu8PildW6/MKzAC5BRAAUW/aZPPzBzAD5BeA8/3oL8SedfbFgikntwD29vc2cH4cOThjU78VCokCkncX9zdCoBX+XCDawnUPGWIVEH+hB1YFwgrtHTM0E0cAOvR9hwT9gwtx54k7YQoTwLp8NJnLb0EuriiE6JBo14jux0+bP1zDBChMAEn99/s9mvARTAYHDaPpPj5+tHdfO1AQhQogqZ8/XNGPNZgcDol8XFSyldsJkpMzg7/zbndX7uX4O8Qx57zGu+zn9tYSyn+8u/hafiaEOE2+18OkrXFEQv8VfnYWclmAdf71AwPRoEW/CZqlDH8UAW6i7pELTXNu9fP7HQHsAEGYkAZjjfbGwiFkJJMAMrSx7ypHlAXuyN+lp7/ZXKwFr6mffWnS5D5E3O5IwaDyymTAq4jQcV3shEWRThW5uFESgRwlf3rapZfQAU20BZCLNyqVG8oAq6FJ7If3Ze384RbD18XPxOFcHNu/LjeDz0J6lsoYdM2d2+3WdEXQEiB28X3CRZBqaKR9fye6CzR57EQ9EyvztyqWkEUELSfIKpWWSHgb4SLI3lhwaHmJ+1M6PcFwPWrx3hi0GMHdXVBAzg3n569AA2UBvLI3PbyNFUFtMmlEYcfdQG/W9oWKR/qHpDFGxhPCql98Vc5FlASQDY+osjcSWQSd349Yifv0vB4b3jj/G2KwWo/mcAxXqHt6jUIsVQAZa4UAveyu++wEf00yY2EYbyFuchV+MFxIr6fVYKEw3FIpxFIFIJOWocwERWR/IMoJxVWN0mSti8f34c/7Sc6OV0SBLyJtFx0RTDZX2Uu7aC7tAjInvbRWvDgz6/KzaW+8JEi812uQR18Ne3Qm+AlldhYlSafAsMOYsUo270+eKsjh0P42Ugur3sAgX14j+ZJ0TNCAnJUzHLw3txdMV72tAHydVhLl8Xdk9kiR5JYspUEDjZkvpcr/gB75t4Cq9x1APQFz+H9aBIWlVvB7P0/QcGjwsmjG4CfQIKZdN0KqAOQAT0EDEswMTqAflkb2YlpoDMIDiwiKq4KgwivtmlQB2lvLJ5pWYA697/PziT8TcTQWGtHYjdkKoRkatvzR30omKELbxSZrO0m7TikPUJ7sYNC+9/WiQd/zR2WJXKRmeCeDJIlVXlmgiJddGoZS9qgkgD9Zcl6qkPcdLFZ6/r73HssS7W1qc8U0VL17R0wYldvsDMV+Wnb5MlVF+nFc1XmtBK2Acv2aJ0JEhhYQaHxyyLxF99NwE1TgcPhpc+kaFNEuh6nOb5A7VnobweaHVxlyLjPKar+B8pIvkH/wwl/kDLEphQOlB8Jhe3upARpkaohoiNAhM66NlMhkAYbBVsJvKXdDNcPiJZlbYt6E5b5Mb4PL1rbSiXHc2UIi5JypkbJv/5bu8aPI1xPUaFsNDkiS+oG6Zwuet6fMMs9JdCFtcR2/ALKtTb6R9vWfyLgTPvAgf7BD/qCVOgo5ZN5bbsY1UlQp9GQIXbeBiO+1bozoJSY0VL0ER8Z41TCX+ngomKEQgKuqpjzWS0zqA1IHmARTz0lSKFyAINbZv2uIbA2QvU3xE85YaEw4W4iymqxMVIAg0jKoq2PS5KsM5ekO/hj8njLN07CDTNgKnfBhTFb+NwGyknTsHj6MyUL+vxGaMHGFWFSZnYWpFyDxbEGI3H+HNPUCSNr+cdlYgUOJUK4cQDITAkjCx+6DLBByMvVOMIhfUfrdYt5dauTNAktKSkpKSkpKvmn+A40c57QrORjCAAAAAElFTkSuQmCC",
    "github-icon": "data:image/png;base64,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",
    "google-icon": "data:image/png;base64,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",
    "envelope-icon": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAMAAACdt4HsAAABX1BMVEUAAAAAAACAgIBAQEBmZmZVVVVJSUlAYGBVVVVNTU1OTk5JSVtVVVVLS1pVVVVVVVVSUlxOTlhPT1hSUlpQUFhNVVVTU1pQUFdOVVVOVVVNU1lPVVVNU1lOU1hNUldQUFpOU1hNUldQUFpPVFhOUlZRUVlQVFhOUlZNUVlQVFdRUVdPU1lNUVdOUVdPUlhOUVdPUlhOUVdQU1lPUVdPUVdOU1hQUlhPUllOUVhOU1dPU1dQUlhQUlhPUVlPU1hPUldPUlhPUllPUlhOUVhQU1lPUlhPUldQU1hPUlhPUldQU1hPUlhPUldOU1hQUlhPUllPUllPUlhPUlhPUlhQUlhPUlhQUlhPUlhPU1dOUlhPUlhPUlhPUlhPUlhPUlhPUlhOUlhPUlhPUlhPUlhPU1hPUldPUlhPUVhPUllPUlhPUlhPUlhPUlhPUlhPUlhPUlhPUlhPUlhPUlhPUlj////CPyOeAAAAc3RSTlMAAQIEBQYHCAkKDQ4PERIVGRodHyAhIiMkJygqKzEyMzQ1Njo7P0BBQkZMTU9SVFVXWFleYWJjZGVve32AipGboqSlpqqrrK2ur7Cxtba9vsHExsfKy83Oz9DT2dzh5+jq6+zt7u/w8fLz9Pb3+Pn7/P3+gUuY6QAAAAFiS0dEdN9tqG0AAAHQSURBVBgZ7cFpVxJhGAbgmwFLi7KksqIFbLVNy0opRDORskXNFjMNAgTbGJj7/5/TI/FwhnEw5v3UB64LfX19bmO5IgMpLiXhMlNnYPY02sbqNGAnoHI0koUq0kgByqERB4qGoHZpZBfqOY0sQEVXaWA1irZwusGAnEwEbrfLDKR6Dx6x9wxg4yzc4hEAg3Ps2dwggMgFqNr6KYjJCntSmYSIrdegyOp9iNgae/BhFOJWiYSimB8CEE43+A9OZgBAON0gCcU9n89DjOd5oPw4xMga90Cx6WcKYvgND/D2BMSdIpug2JKNAgilauzCTlsADmUc/gVF9eUiRGKLvravQpzboIJi2+9UCMDRBfrIHYOY+s42KLosH4eY+kGPXymII8/oAkW37SsQ8U122IxDJLfoBsUOdtoCcDhDl/khAKFUjR2g6LFyEuLuDluqDyCGX9MDil75mxBnXrLpxWmIG1/pBcV96k8tiOuvyuXlaxDWkzr3gaKPd6NwGVmhDyj6qTy20GI93KEfKPr7NBGGCE98pD8odlPKzs5mS+wGioagaAiKhqBoCMqhEQfqG40UoJZoZBEqadOAfQlt0zYDsx/BJZEtMJDC4mX09f1H/gCwBaoMN31WiQAAAABJRU5ErkJggg=="
}
tree_view = None
orig_layout = None
NO_ID = 'NO_ID'
CODETIME_TREEVIEW_NAME = 'Code Time Tree View'
REMOTE_URL = None
shouldOpen = False 
phantom_set = None 
mainSections = ['code-time-actions', 'activity-metrics', 'contributors-node']

def setShouldOpen(val):
    global shouldOpen
    shouldOpen = val

'''
Because we do frequent tree updates/refreshes, we don't want to redraw the tree in its unopened
state, especially if the user is in the middle of using it. This data struct keeps track of what
was opened so state can be maintained across draws.
'''
open_state = set()

# IDs for code time action buttons
CODE_TIME_ACTIONS = {'advanced-metrics', 'open-dashboard', 'toggle-status-metrics', 'learn-more', 'submit-feedback', 'google-signup', 'github-signup', 'email-signup'}

LINK_IDS = set()

# TODO: rare bug where tree isn't clickable (possibly slow wifi)
class OpenTreeView(sublime_plugin.WindowCommand):

    def run(self):
        if not shouldOpen:
            return

        global tree_view 
        global orig_layout
        global phantom_set
        self.currentKeystrokeStats = SessionSummary()
        window = self.window

        orig_view = window.active_view()
        
        # Create tree view if it doesn't exist yet
        if tree_view is None:
            layout = window.get_layout()
            layout['cols'] = [0, 1]
            layout['rows'] = [0, 1]
            layout['cells'] = [[0,0,1,1]]
            window.set_layout(layout)
            self.build_tree_layout()

        phantom_set = sublime.PhantomSet(tree_view, 'software_tree')

        if len(window.views()) == 1:
            window.focus_group(1)

        statusBarMessage = 'Hide status bar metrics' if getValue("show_code_time_status", True) else 'Show status bar metrics'

        self.tree = { 
        	'index': 0,
        	'depth': 0,
        	'path': '',
        	'name': '',
            'id': '',
        	'dir': True,
        	'expanded': False,
        	'childs': [
                {
                    'depth': 1,
                    'id': 'code-time-actions',
                    'name': 'CODE TIME',
                    'dir': True,
                    'expanded': True,
                    'childs': [
                        {
                            'depth': 2,
                            'id': 'advanced-metrics',
                            'icon': 'paw',
                            'name': 'See advanced metrics',
                            'dir': False,
                            'expanded': False,
                            'childs': None
                        },
                        { 
                            'depth': 2,
                            'id': 'toggle-status-metrics',
                            'icon': 'visible',
                            'name': statusBarMessage,
                            'dir': False,
                            'expanded': False,
                            'childs': None
                        },
                        { 
                            'depth': 2,
                            'id': 'learn-more',
                            'icon': 'readme',
                            'name': 'Learn more',
                            'dir': False,
                            'expanded': False,
                            'childs': None
                        },
                        {
                            'depth': 2,
                            'id': 'submit-feedback',
                            'icon': 'message',
                            'name': 'Submit feedback',
                            'dir': False,
                            'expanded': False,
                            'childs': None
                        },
                        { 
                            'depth': 2,
                            'id': 'open-dashboard',
                            'icon': 'dashboard',
                            'name': 'View summary',
                            'dir': False,
                            'expanded': False,
                            'childs': None
                        }
                    ]
                }
            ]
        }

        data = getSessionSummaryData()
        codeTimeSummary = getCodeTimeSummary()
        data.update(codeTimeSummary)

        # Build tree nodes
        self.addConnectionStatusIcons()
        self.buildMetricsNodes(data)
        # self.buildCommitTreeNodes()
        self.buildContributorNodes()
        # print(len(self.tree['childs']))
        self.expand(self.tree, '')

    def build_tree_layout(self):
        global tree_view 
        global orig_layout 
        window = self.window 
        # window.set_sidebar_visible(False) 
        layout = window.get_layout()
        orig_layout = deepcopy(layout)
        if len(layout['cols']) < 3:
            layout['cols'] = [0, 0.25, 1]
        elif layout['cols'][1] > 0.3:
            # Evenly space the original views
            tree_view_width = min(0.25, layout['cols'][1] / 2.0)
            new_orig_views = list([x + (1 - x) * tree_view_width for x in layout['cols'][1:-1]]) 
            layout['cols'] = [0, tree_view_width] + new_orig_views + [layout['cols'][-1]]

        layout['cells'] = [[0, 0, 1, len(layout['rows']) - 1]] + [
            [cell[0] + 1, cell[1], cell[2] + 1, cell[3]] for cell in layout['cells']
        ]
        window.set_layout(layout)

        tree_view = window.new_file()
        tree_view.settings().set('line_numbers', False)
        tree_view.settings().set('gutter', False)
        tree_view.settings().set('rulers', [])
        tree_view.set_read_only(True)
        tree_view.set_name(CODETIME_TREEVIEW_NAME)
        tree_view.set_scratch(True)
        if window.num_groups() > 1:
            for view in window.views():
                (group, index) = window.get_view_index(view)
                window.set_view_index(view, group + 1, 0)
            window.set_view_index(tree_view, 0, 0)


    def expand(self, tree, id):
        if 'id' in tree and tree['id'] == id:
            tree['expanded'] = not tree['expanded']
            if tree['expanded'] is True:
                open_state.add(tree['id'])
            else:
                open_state.remove(tree['id'])
            self.rebuild_phantom()
            return True
        else:
            if tree['childs'] is None:
                return False
            else:
                for child in tree['childs']:
                    if self.expand(child, id):
                        return True

    def performCodeTimeAction(self, command):
        if command == 'open-dashboard':
            codetimemetricsthread = Thread(target=launchCodeTimeMetrics)
            codetimemetricsthread.start()
        elif command == 'toggle-status-metrics':
            toggleStatus()
            refreshTreeView()
        elif command == 'learn-more':
            displayReadmeIfNotExists()
        elif command == 'advanced-metrics':
            launchWebDashboardUrl()
        elif command == 'submit-feedback':
            launchSubmitFeedback()
        elif command == 'google-signup':
            launchLoginUrl('google')
        elif command == 'github-signup':
            launchLoginUrl('github')
        elif command == 'email-signup':
            launchLoginUrl('software')
            

    def getAuthTypeLabelAndIcon(self):
        authType = getItem('authType')

        if (authType == 'google'):
            return { "label": 'Connected using Google', "icon": 'google-icon' }
        elif (authType == 'github'):
            return { "label": 'Connected using GitHub', "icon": 'github-icon' }
        elif (authType == 'software'):
            return { "label": 'Connected using email', "icon": 'envelope-icon' }
        return { "label": 'Connected', "icon": 'envelope-icon' } 

    def on_click(self, url):
        comps = url.split('---')

        command = comps[1]

        global UI_INTERACTIONS
        try:
            if command.find("git@github.com:") is 0:
                # clicking the contributors git link sends the command: "git@github.com:swdotcom/swdc-sublime.git"
                # mapping this to a different command lookup key for tracking the UI interaction
                command_lookup_key = 'contributors-repo-link'
            else:
                command_lookup_key = command

            track_ui_interaction(
                jwt=getJwt(), 
                plugin_id=getPluginId(),
                plugin_version=getVersion(),
                plugin_name=getPluginName(),
                **UI_INTERACTIONS[command_lookup_key]
            )
        except Exception as ex:
            print("Cannot track ui interaction for command: %s" % ex)

        # Don't close or open this
        if command in mainSections:
            return

        if command == REMOTE_URL:
            sublime.active_window().run_command('generate_contributor_summary')

        if command in CODE_TIME_ACTIONS:
            self.performCodeTimeAction(command)
            return 

        if command in LINK_IDS:
            webbrowser.open(command)
            return

        if comps[0] == 'expand':
            self.expand(self.tree, command)

        

    '''
    TODO: lots of styles changes to look more like Atom/VSCode, though 
          Sublime's "minihtml" engine has some large restrictions
    '''
    def rebuild_phantom(self):
        global phantom_set 
        result = self.render_subtree(self.tree, [])
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
            .file span {
            font-size: 7px; 
            }
            .file a {
            text-decoration: none;
            padding-bottom: 5px;
            color: var(--foreground);
            }
            .file p {
            position: relative;
            bottom: 2px;
            display: inline;
            }
        </style>''' + ''.join(result) + '</body>'
        self.phantom = sublime.Phantom(sublime.Region(0), html, sublime.LAYOUT_BLOCK, on_navigate=self.on_click)
        phantom_set.update([self.phantom])

    def render_subtree(self, item, result):
        if 'id' in item and item['id'] in open_state:
            item['expanded'] = True

        global icons
        if not item['dir']:
            if 'icon' in item:
                result.append('<div class="file" style="margin-left: {margin}px;"><a href=open---{index}><img height="16" width="16" alt="" src="{icon}"><p> {name}</p></a></div>'.format(
                    margin=(item['depth'] * 15) - 20,
                    index=item['id'] if 'id' in item else NO_ID,
                    name=item['name'],
                    icon=icons[item['icon']]))
                    # icon='🚀'))
                return result
            else:
                result.append('<div class="file" style="margin-left: {margin}px"><a href=open---{index}>{name}</a></div>'.format(
                    margin=(item['depth'] * 15) - 20,
                    index=item['id'] if 'id' in item else NO_ID,
                    name=item['name']))
                return result

        # if in a directory
        if item['depth'] > 0:
            result.append('<div id="{id}" class="dir" style="margin-left: {margin}px"><a href=expand---{index}>{sign}&nbsp;{name}</a></div>'.format(
                id=item['id'] if 'id' in item else NO_ID,
                margin=(item['depth'] * 15) - 20,
                index=item['id'] if 'id' in item else NO_ID,
                name=item['name'],
                sign='' if ('id' in item and item['id'] in mainSections) else ('▼' if (item['expanded']) else '▶')))

        # if directory with things
        if item['childs'] != None and item['expanded']:
            for child in item['childs']:
                self.render_subtree(child, result)

        return result

    def setCurrentKeystrokeStats(self, keystrokeStats):
        if not keystrokeStats:
            self.currentKeystrokeStats = SessionSummary()
        else:
            for key in keystrokeStats.source:
                # fileInfo is of type FileChangeInfo
                fileInfo = keystrokeStats.source[key] 
                self.currentKeystrokeStats.currentDayKeystrokes = fileInfo.keystrokes
                self.currentKeystrokeStats.currentDayLinesAdded = fileInfo.linesAdded
                self.currentKeystrokeStats.currentDayLinesRemoved = fileInfo.linesRemoved

    def addConnectionStatusIcons(self):
        if not getItem('name'):
            self.addSignupButtons()
        else:
            authObj = self.getAuthTypeLabelAndIcon()
            connectedNode = {
                'depth': 2,
                'id': 'connected-type-button',
                'icon': authObj['icon'],
                'name': authObj['label'],
                'dir': False,
                'expanded': False,
                'childs': None
            }
            self.tree['childs'][0]['childs'].insert(0, connectedNode)

    def addSignupButtons(self):
        googleSignup = {
            'depth': 2,
            'id': 'google-signup',
            'icon': 'google-icon',
            'name': 'Sign up with Google',
            'dir': False,
            'expanded': False,
            'childs': None
        }
        githubSignup = {
            'depth': 2,
            'id': 'github-signup',
            'icon': 'github-icon',
            'name': 'Sign up with GitHub',
            'dir': False,
            'expanded': False,
            'childs': None
        }
        emailSignup = {
            'depth': 2,
            'id': 'email-signup',
            'icon': 'envelope-icon',
            'name': 'Sign up with email',
            'dir': False,
            'expanded': False,
            'childs': None
        }
        self.tree['childs'][0]['childs'] = [googleSignup, githubSignup, emailSignup] + self.tree['childs'][0]['childs']

    # data is an object of shape returned by SessionSummary()
    def buildMetricsNodes(self, data):
        # delete the current (ACTIVITY METRICS) from tree['childs']
        self.tree['childs'] = list([x for x in self.tree['childs'] if x['name'] != 'DAILY METRICS'])

        newActivityMetrics = {
            'depth': 1,
            'id': 'activity-metrics',
            'name': 'DAILY METRICS',
            'dir': True,
            'expanded': True,
            'childs': []
        }

        # EDITOR-TIME stuff
        editorMinutes = humanizeMinutes(data['codeTimeMinutes']).strip()
        newActivityMetrics['childs'].append(self.buildCodeTimeMetricsItem('code-time', 'Code time', editorMinutes))

        # CODE-TIME stuff
        codeTimeMinutes = humanizeMinutes(data['activeCodeTimeMinutes']).strip()
        avgDailyMinutes = humanizeMinutes(data['averageDailyMinutes']).strip()
        globalAvgMinutes = humanizeMinutes(data['globalAverageSeconds'] / 60).strip()
        boltIcon = 'bolt' if data['currentDayMinutes'] > data['averageDailyMinutes'] else 'bolt-grey'
        newActivityMetrics['childs'].append(self.buildCodeTimeMetricsItem('active-code-time', 'Active code time', codeTimeMinutes, avgDailyMinutes, globalAvgMinutes, boltIcon))

        currLinesAdded = self.currentKeystrokeStats['currentDayLinesAdded'] + data['currentDayLinesAdded']
        linesAdded = formatNumWithK(currLinesAdded)
        avgLinesAdded = formatNumWithK(data['averageLinesAdded'])
        globalLinesAdded = formatNumWithK(data['globalAverageLinesAdded'])
        boltIcon = 'bolt' if data['currentDayLinesAdded'] > data['averageLinesAdded'] else 'bolt-grey'
        newActivityMetrics['childs'].append(self.buildCodeTimeMetricsItem('lines-added', 'Lines added', linesAdded, avgLinesAdded, globalLinesAdded, boltIcon))

        currLinesRemoved = self.currentKeystrokeStats['currentDayLinesRemoved'] + data['currentDayLinesRemoved']
        linesRemoved = formatNumWithK(currLinesRemoved)
        avgLinesRemoved = formatNumWithK(data['averageLinesRemoved'])
        globalLinesRemoved = formatNumWithK(data['globalAverageLinesRemoved'])
        boltIcon = 'bolt' if data['currentDayLinesRemoved'] > data['averageLinesRemoved'] else 'bolt-grey'
        newActivityMetrics['childs'].append(self.buildCodeTimeMetricsItem('lines-removed', 'Lines removed', linesRemoved, avgLinesRemoved, globalLinesRemoved, boltIcon))

        currKeystrokes = self.currentKeystrokeStats['currentDayKeystrokes'] + data['currentDayKeystrokes']
        keystrokes = formatNumWithK(currKeystrokes)
        avgKeystrokes = formatNumWithK(data['averageDailyKeystrokes'])
        globalKeystrokes = formatNumWithK(data['globalAverageDailyKeystrokes'])
        boltIcon = 'bolt' if data['currentDayKeystrokes'] > data['averageDailyKeystrokes'] else 'bolt-grey'
        newActivityMetrics['childs'].append(self.buildCodeTimeMetricsItem('keystrokes', 'Keystrokes', keystrokes, avgKeystrokes, globalKeystrokes, boltIcon))
        
        
        # Num files changed
        fileChangeInfoMap = getFileChangeSummaryAsJson()
        topFilesNode = self.buildTopFilesNode(fileChangeInfoMap)
        if topFilesNode:
            newActivityMetrics['childs'].append(topFilesNode)

        # More file metrics nodes
        fileChangeInfos = fileChangeInfoMap.values()

        topKpmFileNodes = self.topFilesMetricsNode(fileChangeInfos, 'Top files by KPM', 'kpm', 'top-kpm-files')
        if topKpmFileNodes:
            newActivityMetrics['childs'].append(topKpmFileNodes)

        topKeystrokeFileNodes = self.topFilesMetricsNode(fileChangeInfos, 'Top files by keystrokes', 'keystrokes', 'top-keystrokes-files')
        if topKeystrokeFileNodes:
            newActivityMetrics['childs'].append(topKeystrokeFileNodes)

        topCodetimeFileNodes = self.topFilesMetricsNode(fileChangeInfos, 'Top files by code time', 'duration_seconds', 'top-codetime-files')
        if topCodetimeFileNodes:
            newActivityMetrics['childs'].append(topCodetimeFileNodes)

        folders = getOpenProjects()
        
        openChangesNode = {
            'depth': 2,
            'id': 'open-changes',
            'name': 'Open changes',
            'dir': True,
            'expanded': False,
            'childs': []
        }
        committedTodayNode = {
            'depth': 2,
            'id': 'committed-today',
            'name': 'Committed today',
            'dir': True,
            'expanded': False,
            'childs': []
        }
        
        if len(folders) > 0:
            for i in range(len(folders)):
                directory = folders[i]
                basename = os.path.basename(directory)

                # Add uncommitted changes
                currentChangesSummary = getUncommittedChanges(directory)
                uncommittedNode = self.buildOpenChangesDirNodeItem(basename, 'uncommitted-{}'.format(i), currentChangesSummary['insertions'], currentChangesSummary['deletions'])
                openChangesNode['childs'].append(uncommittedNode)

                # Add committed changes
                todaysChangeSummary = getTodaysCommits(directory)
                committedNode = self.buildOpenChangesDirNodeItem(basename, 'committed-{}'.format(i), todaysChangeSummary['insertions'], todaysChangeSummary['deletions'], todaysChangeSummary['commitCount'], todaysChangeSummary['fileCount'])
                committedTodayNode['childs'].append(committedNode)

            newActivityMetrics['childs'].append(openChangesNode)
            newActivityMetrics['childs'].append(committedTodayNode)

        # Insert newActivityMetrics into second position of tree['childs']
        self.tree['childs'].insert(1, newActivityMetrics)


    def buildCodeTimeMetricsItem(self, id, label, todayValue, avgValue=None, globalAvgValue=None, avgIcon=None):
        todayString = datetime.today().strftime('%a')
        item = {
            'depth': 2,
            'id': id,
            'name': label,
            'dir': True,
            'expanded': False,
            'childs': [
                {
                    'depth': 3,
                    'icon': 'rocket',
                    'name': 'Today: {}'.format(todayValue),
                    'dir': False,
                    'expanded': False,
                    'childs': None
                }
            ]
        }

        if avgValue and globalAvgValue:
            item['childs'].append({
                    'depth': 3,
                    'icon': avgIcon,
                    'name': 'Your average ({}): {}'.format(todayString, avgValue),
                    'dir': False,
                    'expanded': False,
                    'childs': None
                })
            item['childs'].append({
                    'depth': 3,
                    'icon': 'global-grey',
                    'name': 'Global average ({}): {}'.format(todayString, globalAvgValue),
                    'dir': False,
                    'expanded': False,
                    'childs': None
                })

        return item 

    def buildTopFilesNode(self, fileChangeInfoMap):
        topFileTreeNodes = {
            'depth': 2,
            'id': 'files-changed',
            'name': 'Files changed today',
            'dir': True,
            'expanded': False,
            'childs': [
                {
                    'depth': 3,
                    'name': '',
                    'dir': False,
                    'expanded': False,
                    'childs': None
                }
            ]
        }
        filesChanged = len(fileChangeInfoMap.keys()) if fileChangeInfoMap else 0

        if filesChanged > 0:
            topFileTreeNodes['childs'][0]['name'] = 'Today: {}'.format(filesChanged)
            return topFileTreeNodes
        else:
            return {}

    def buildOpenChangesDirNodeItem(self, dirName, id, insertions, deletions, commitCount=None, fileCount=None):
        newNode = {
            'depth': 3,
            'id': id,
            'name': dirName,
            'dir': True,
            'expanded': False,
            'childs': []
        }

        newNode['childs'].append({
            'depth': 4,
            'icon': 'insertion',
            'name': 'Insertion(s): {}'.format(insertions),
            'dir': False,
            'expanded': False,
            'childs': None 
        })
        newNode['childs'].append({
            'depth': 4,
            'icon': 'deletion',
            'name': 'Deletions(s): {}'.format(deletions),
            'dir': False,
            'expanded': False,
            'childs': None 
        })

        if commitCount:
            newNode['childs'].append({
                'depth': 4,
                'icon': 'commit',
                'name': 'Commit(s): {}'.format(commitCount),
                'dir': False,
                'expanded': False,
                'childs': None 
            })  
            newNode['childs'].append({
                'depth': 4,
                'icon': 'files',
                'name': 'Files changed: {}'.format(fileCount),
                'dir': False,
                'expanded': False,
                'childs': None 
            })

        return newNode


    def topFilesMetricsNode(self, fileChangeInfos, name, sortBy, id):
        if not fileChangeInfos or len(fileChangeInfos) == 0:
            return None 

        node = {
            'depth': 2,
            'id': id,
            'name': name,
            'dir': True,
            'expanded': False,
            'childs': []
        }

        sortedArr = []
        if sortBy == 'duration_seconds' or sortBy == 'kpm' or sortBy == 'keystrokes':
            sortedArr = list(sorted(fileChangeInfos, key=lambda info: info[sortBy], reverse=True))
        else:
            log('Sorting by invalid sortBy value: "{}"'.format(sortBy))

        childrenNodes = []
        length = min(3, len(sortedArr))
        for i in range(0, length):
            sortedObj = sortedArr[i]
            fileName = sortedObj['name']

            val = 0
            if sortBy == 'kpm' or sortBy == 'keystrokes':
                val = formatNumWithK(sortedObj['kpm'] or 0)
            elif sortBy == 'duration_seconds':
                minutes = sortedObj.get('duration_seconds', 0) / 60
                val = humanizeMinutes(minutes)

            fsPath = sortedObj['fsPath']
            label = '{} | {}'.format(fileName, val)

            valItem = {
                'depth': 3,
                'name': label,
                'dir': False,
                'expanded': False,
                'childs': None 
            }

            node['childs'].append(valItem)
        
        return node 

    # TODO: work on the CSS for this
    def buildContributorNodes(self):
        self.tree['childs'] = list([x for x in self.tree['childs'] if x['name'] != 'CONTRIBUTORS'])

        newContributorsNodes = {
            'depth': 1,
            'id': 'contributors-node',
            'name': 'CONTRIBUTORS',
            'dir': True,
            'expanded': True,
            'childs': []
        }
        liItems = []
        projectDir = getProjectDirectory()
        # print('projectDir is {}'.format(projectDir))

        if projectDir:
            contributorMembers = getRepoContributors(projectDir)
            remoteUrl = getRepoUrlLink(projectDir)

            if contributorMembers and len(contributorMembers) > 0:
                title = {
                    'depth': 2,
                    'id': contributorMembers[0]['identifier'],
                    'name': contributorMembers[0]['identifier'],
                    'dir': False,
                    'expanded': False,
                    'childs': None 
                }
                liItems.append(title)
                global CODE_TIME_ACTIONS
                CODE_TIME_ACTIONS.add(contributorMembers[0]['identifier'])
                global REMOTE_URL
                REMOTE_URL = contributorMembers[0]['identifier']

                for i in range(len(contributorMembers)):
                    contributor = contributorMembers[i]
                    lastCommitInfo = getLastCommitId(projectDir, contributor['email'])

                    memberId = 'member-{}'.format(contributor['email'])
                    contributorNode = self.buildContributorLiItem(memberId, contributor['email'], lastCommitInfo, remoteUrl)
                    liItems.append(contributorNode)

        newContributorsNodes['childs'] = liItems
        self.tree['childs'].append(newContributorsNodes)

    def buildContributorLiItem(self, memberId, label, lastCommitInfo, remoteUrl):
        link = ''
        if lastCommitInfo:
            link = '{}/commit/{}'.format(remoteUrl, lastCommitInfo['commitId'])
        
        liItem = {
            'depth': 2,
            'id': memberId,
            'name': label,
            'dir': True,
            'expanded': False,
            'childs': []  
        }

        if lastCommitInfo:
            global LINK_IDS
            LINK_IDS.add(link)
            child = {
                'depth': 3,
                'id': link,
                'name': lastCommitInfo['comment'],
                'dir': False,
                'expanded': False,
                'childs': None 
            }
            liItem['childs'].append(child)

        return liItem

# If the tree view is closed, collapse its view and set the layout back to its original.
# TODO: improvements for this method needed b/c the tree view is itself part of the user's 
#       view layout and it's difficult to return to that state 
def handleCloseTreeView():
    global shouldOpen
    global tree_view
    shouldOpen = False
    tree_view = None
    # global orig_layout
    
    # groups = set()
    # window = sublime.active_window()
    # for view in window.views():
    #     (group, _) = window.get_view_index(view)
    #     groups.add(group)
    # for group in groups:
    #     views = window.views_in_group(group)
    #     for view in reversed(views):
    #         # Shift the views back
    #         window.set_view_index(view, group - 1, 0)

    # window.set_layout(orig_layout)
    # orig_layout = None
