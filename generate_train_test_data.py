import pickle, os, glob
import argparse
import pandas as pd
import json
from collections import Counter
def save_data(filename, data):
    print("data is saved at:", filename)
    f = open(filename, 'wb')
    pickle.dump(data, f)
    f.close()

def load_data(filename):
    print("strating to load data from:", filename)
    f = open(filename, 'rb')
    data = pickle.load(f)
    f.close()
    return data

def parse_options():
    parser = argparse.ArgumentParser(description='Generate and split train datasettest_data.')
    parser.add_argument('-i', '--input', help='The path of a dir which consists of some pkl_files')
    parser.add_argument('-o', '--out', help='The path of output.', required=True)
    parser.add_argument('-n', '--num',type=int, help='Num of K-fold.')
    parser.add_argument('-d', '--dataset', help='Dataset name',default=False, action='store_true')
    parser.add_argument('-g', '--graph', help='Graph path', type=str, choices=['ast', 'cfg', 'ddg', 'pdg'])
    args = parser.parse_args()
    return args
    
def generate_dataframe(input_path, save_path):
    input_path = input_path + "/" if input_path[-1] != "/" else input_path
    save_path = save_path + "/" if save_path[-1] != "/" else save_path
    os.makedirs(save_path, exist_ok=True)
    dic = []
    for dataset_name in os.listdir(input_path):
        datas = os.listdir(input_path + dataset_name)
        for dataname in datas:
            data = ()
            for graph in glob.glob(f"{input_path}{dataset_name}/{dataname}/*.pkl"):
                data += (load_data(graph),)
            dic.append({
                "dataname": dataname, 
                "length":   len(data[0][0]),
                "data":     data, 
                "label":    0 if dataset_name == "No-Vul" else 1})
    final_dic = pd.DataFrame(dic)
    save_data(save_path + "all_data.pkl", final_dic)

def gather_data(input_path, output_path, graph="*"):
    input_path = input_path + "/" if input_path[-1] != "/" else input_path
    output_path = output_path + "/" if output_path[-1] != "/" else output_path
    output = []
    if graph != "*":
        output.append(output_path + f"{graph}_pkl/")
        output.append(output_path + f"without_{graph}_pkl/")
    else:
        output.append(output_path)
    os.makedirs(output[0], exist_ok=True)
    for set in ["train", "test", "valid"]:
        dic = []
        datapath = input_path[:input_path.find('processed')] + f"{set}_cdata.jsonl"
        with open(datapath, "r") as f:
            for line in f:
                js = json.loads(line)
                data = ()
                for graph_data in glob.glob(f"{input_path}{js['idx']}/{graph}.pkl"):
                    data += (load_data(graph_data),)
                lengths = len(data[0][0])
                dic.append({
                    "dataname": js['idx'], 
                    "length":   lengths,
                    "data":     data, 
                    "label":    js['target']})
        final_dic = pd.DataFrame(dic)
        save_data(output[0] + f"{set}.pkl", final_dic)
    if graph != "*":
        os.makedirs(output[1], exist_ok=True)
        for set in ["train", "test", "valid"]:
            dic = []
            datapath = input_path[:input_path.find('processed')] + f"{set}_cdata.jsonl"
            with open(datapath, "r") as f:
                for line in f:
                    js = json.loads(line)
                    data = ()
                    for graph_data in glob.glob(f"{input_path}{js['idx']}/*.pkl"):
                        if graph not in graph_data:
                            data += (load_data(graph_data),)
                    lengths = len(data[0][0])
                    for d in data:
                        for i in d:
                            if len(i) > lengths:
                                lengths = len(i)
                    dic.append({
                        "dataname": js['idx'], 
                        "length":   lengths,
                        "data":     data, 
                        "label":    js['target']})
            final_dic = pd.DataFrame(dic)
            save_data(output[1] + f"{set}.pkl", final_dic)

def split_data(all_data_path, save_path, kfold_num):
    df_test = load_data(all_data_path)
    save_path = save_path + "/" if save_path[-1] != "/" else save_path
    seed = 0
    df_dict = {}
    train_dict = {i:{} for i in range(kfold_num)}
    test_dict = {i:{} for i in range(kfold_num)}
    from sklearn.model_selection import KFold
    kf = KFold(n_splits = kfold_num, shuffle = True, random_state = seed)
    for i in Counter(df_test.label.values):
        df_dict[i] = df_test[df_test.label == i]
        for epoch, result in enumerate(kf.split(df_dict[i])):
            train_dict[epoch][i]  = df_dict[i].iloc[result[0]]
            test_dict[epoch][i] =  df_dict[i].iloc[result[1]] 
    train_all = {i:pd.concat(train_dict[i], axis=0, ignore_index=True) for i in train_dict}
    test_all = {i:pd.concat(test_dict[i], axis=0, ignore_index=True) for i in test_dict}
    save_data(save_path + "train.pkl", train_all)
    save_data(save_path + "test.pkl", test_all)

def main():
    args = parse_options()
    input_path = args.input
    output_path = args.out
    kfold_num = args.num
    graph = args.graph
    if args.dataset:
        gather_data(input_path, output_path, graph)
    else:
        generate_dataframe(input_path, output_path)
        split_data(output_path + "/all_data.pkl", output_path, kfold_num)
    

if __name__ == "__main__":
    main()