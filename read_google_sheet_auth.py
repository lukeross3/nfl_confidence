import gspread as gs
import pandas as pd

from utils import get_ranks

gc = gs.service_account(filename="secrets/lukeross-59c98137a1cf.json")
sh = gc.open("Luke Confidence 21-22")
ws = sh.worksheet("Week 1")
df = pd.DataFrame(ws.get_all_records())
df.confidence = get_ranks(values=df.avg, zero_indexed=False)
print(df)
