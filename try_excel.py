import pandas as pd
import json


with open('jobs.json', 'r') as file:
    results = json.load(file)

df = pd.DataFrame(results)
df.to_excel('jobs.xlsx', index=False)