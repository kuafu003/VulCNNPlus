# coding=utf-8
import os
import re
import shutil
import argparse
import json
from clean_gadget import clean_gadget

def parse_options():
    parser = argparse.ArgumentParser(description='Normalization.')
    parser.add_argument('-i', '--input', help='The dir path of input dataset', type=str, required=True)
    parser.add_argument('-d', '--dataset', help='nobalance dataset',default=False, action='store_true')
    args = parser.parse_args()
    return args

def normalize(path):
    setfolderlist = os.listdir(path)
    for setfolder in setfolderlist:
        if "." in setfolder:
            pro_one_file(path + "/" + setfolder)
            continue
        catefolderlist = os.listdir(path + "//" + setfolder)
        #print(catefolderlist)
        for catefolder in catefolderlist:
            filepath = path + "//" + setfolder + "//" + catefolder
            print(catefolder)
            pro_one_file(filepath)

def pro_one_file(filepath):
    with open(filepath, "r") as file:
        code = file.read()
    file.close()
    # code = re.sub('(?<!:)\\/\\/.*|\\/\\*(\\s|.)*?\\*\\/', "", code)
    code = re.sub(r"""
    (?<!:)
    //.*?$
    |
    /\*.*?\*/
    """, "", code, flags=re.DOTALL | re.MULTILINE | re.VERBOSE)
    # print(code)
    with open(filepath, "w") as file:
        file.write(code.strip())
    file.close()

    with open(filepath, "r") as file:
        org_code = file.readlines()
        # print(org_code)
        nor_code = clean_gadget(org_code)
    file.close()
    with open(filepath, "w") as file:
        file.writelines(nor_code)
    file.close()

def main():
    args = parse_options()
    if args.dataset:
        if not os.path.exists(args.input + "/normalized"):
            os.mkdir(args.input + "/normalized")
        for set in ["train", "test", "valid"]:
            with open(args.input + f"/{set}_cdata.jsonl", "r") as f:
                for line in f:
                    js = json.loads(line)
                    with open(args.input + f"/normalized/{js['idx']}.c", "a") as f1:
                        f1.write(js['func'])
                    f1.close()
            f.close()
        normalize(args.input+"/normalized")
    else:
        normalize(args.input)
    

if __name__ == '__main__':
    main()
    # for a test
    # pro_one_file('./dataset/nobalance_BigVul/normalized/17681.c')