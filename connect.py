"""Cria um SQLite fictício para praticar a troca de fonte do chatbot."""
import argparse
from pathlib import Path
import sqlite3
from data_sources import open_source


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('target',type=Path)
    args=parser.parse_args()
    if args.target.exists():
        parser.error('Escolha um arquivo novo; o comando não sobrescreve bancos existentes.')
    args.target.parent.mkdir(parents=True,exist_ok=True)
    source=open_source()
    target=sqlite3.connect(args.target)
    try:
        source.connection.backup(target)
        target.commit()
    finally:
        target.close();source.close()
    print('SQLite fictício criado. Use python app.py --source sqlite --input '+str(args.target))


if __name__=='__main__':main()
