"""Developer-only importer. zstandard is not a runtime dependency of the app."""
import csv
from datetime import date
from dataclasses import asdict
import gzip
import hashlib
import io
import json
from pathlib import Path
import sys
from urllib.request import Request,urlopen

import zstandard

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tactics import THEMES,parse_database_row

URL='https://database.lichess.org/lichess_db_puzzle.csv.zst'


def main():
    directory=ROOT/'data/tactics';directory.mkdir(parents=True,exist_ok=True)
    temporary=directory/'puzzles.pending.gz'
    counts={theme:0 for theme in THEMES.values() if theme!='mix'}
    total=scanned=rejected=0;ids=set()
    request=Request(URL,headers={'User-Agent':'CoachChess-offline-bank/1.0'})
    with urlopen(request,timeout=60) as response, zstandard.ZstdDecompressor().stream_reader(response) as stream:
        with io.TextIOWrapper(stream,encoding='utf8') as text,gzip.open(temporary,'wt',encoding='utf8',compresslevel=6) as output:
            for row in csv.DictReader(text):
                scanned+=1
                if scanned>250000:break
                tags=row['Themes'].split()
                needed=any(counts.get(tag,40)<40 for tag in tags)
                if total>=30000 and not needed:continue
                try:puzzle=parse_database_row(row)
                except ValueError:rejected+=1;continue
                if puzzle.id in ids:continue
                ids.add(puzzle.id);output.write(json.dumps(asdict(puzzle),separators=(',',':'))+'\n');total+=1
                for tag in puzzle.themes:
                    if tag in counts:counts[tag]+=1
                if total>=30000 and min(counts.values())>=40:break
                if scanned>=250000:break
    if min(counts.values())<1:raise RuntimeError('Faltam temas no banco local; não será publicado.')
    target=directory/'puzzles.jsonl.gz';temporary.replace(target)
    manifest={'source':URL,'license':'CC0-1.0','prepared':str(date.today()),'count':total,
              'scanned':scanned,'rejected':rejected,'themes':counts,'sha256':hashlib.sha256(target.read_bytes()).hexdigest()}
    (directory/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
    print(json.dumps(manifest,indent=2))


if __name__=='__main__':main()
