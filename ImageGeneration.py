import networkx as nx
import numpy as np
import argparse
import os
import sent2vec
import pickle
import glob
import re
from multiprocessing import Pool
from functools import partial

def parse_options():
    parser = argparse.ArgumentParser(description='Image-based Vulnerability Detection.')
    parser.add_argument('-i', '--input', help='The path of a dir which consists of some dot_files')
    parser.add_argument('-o', '--out', help='The path of output.', required=True)
    parser.add_argument('-m', '--model', help='The path of model.', required=True)
    args = parser.parse_args()
    return args

def graph_extraction(dot):
    graph = nx.drawing.nx_pydot.read_dot(dot)
    return graph

def sentence_embedding(sentence):
    emb = sent2vec_model.embed_sentence(sentence)
    return emb[0]

def image_generation(dot):
    try:
        graph = graph_extraction(dot)
        labels_dict = nx.get_node_attributes(graph, 'label')
        labels_code = dict()
        for label, all_code in labels_dict.items():
            all_code = re.sub(r'<SUB>\d+</SUB>', '', all_code)[1:-1]
            code = all_code[all_code.index(",") + 1:-1].split("\\n")[0]
            code = code.replace("static void", "void")
            labels_code[label] = code
    
        degree_cen_dict = nx.degree_centrality(graph)
        closeness_cen_dict = nx.closeness_centrality(graph)
        harmonic_cen_dict = nx.harmonic_centrality(graph)
        katz_cen_dict = nx.katz_centrality(graph)
        betweenness_cen_dict = nx.betweenness_centrality(graph)
        eigenvector_cen_dict = nx.eigenvector_centrality(graph)
    
        G = nx.DiGraph()
        G.add_nodes_from(graph.nodes())
        G.add_edges_from(graph.edges())
        max_iter = 500
        tol = 1e-4
        while(1):
            if G.number_of_nodes() == 0: 
                katz_cen_dict = {}
                break
            try:
                katz_cen_dict = nx.katz_centrality(G, max_iter=max_iter, tol=tol)
                break
            except:
                max_iter += 100
                tol *= 10
                print(f"katz_cen_dict -- max_iter: {max_iter}, tol: {tol}")
                continue
        max_iter = 500
        tol = 1e-4
        while(1):
            if G.number_of_nodes() == 0: 
                eigenvector_cen_dict = {}
                break
            try:
                eigenvector_cen_dict = nx.eigenvector_centrality(G, max_iter=max_iter, tol=tol)
                break
            except Exception as e:
                max_iter += 100
                if tol < 1: tol *= 10
                print(f"eigenvector_cen_dict -- max_iter: {max_iter}, tol: {tol}")
                if max_iter > 10000: 
                    print(f"An error occurred: {e}")
                    print(f"dot: {dot}")
                    break
                continue
    
        degree_channel = []
        closeness_channel = []
        betweenness_channel = []
        eigenvector_channel = []
        harmonic_channel = []
        katz_channel = []
        for label, code in labels_code.items():
            line_vec = sentence_embedding(code)
            line_vec = np.array(line_vec)
    
            degree_cen = degree_cen_dict[label]
            degree_channel.append(degree_cen * line_vec)
    
            closeness_cen = closeness_cen_dict[label]
            closeness_channel.append(closeness_cen * line_vec)

            betweenness_cen = betweenness_cen_dict[label]
            betweenness_channel.append(betweenness_cen * line_vec)

            eigenvector_cen = eigenvector_cen_dict[label]
            eigenvector_channel.append(eigenvector_cen * line_vec)

            harmonic_cen = harmonic_cen_dict[label]
            harmonic_channel.append(harmonic_cen * line_vec)
    
            katz_cen = katz_cen_dict[label]
            katz_channel.append(katz_cen * line_vec)
    
        return (degree_channel, closeness_channel, katz_channel, betweenness_channel, eigenvector_channel, harmonic_channel)
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def write_to_pkl(dot, out, existing_files):
    dot_name = dot.split('/')[-1].split('.dot')[0]
    if dot_name in existing_files:
        return None
    else:
        print(dot_name)
        channels = image_generation(dot)
        if channels == None:
            return None
        else:
            (degree_channel, closeness_channel, katz_channel, betweenness_channel, eigenvector_channel, harmonic_channel) = channels
            out_pkl = out + dot_name + '.pkl'
            data = [degree_channel, closeness_channel, katz_channel, betweenness_channel, eigenvector_channel, harmonic_channel]
            with open(out_pkl, 'wb') as f:
                pickle.dump(data, f)

def main():
    args = parse_options()
    dir_name = args.input
    out_path = args.out
    trained_model_path = args.model
    global sent2vec_model
    sent2vec_model = sent2vec.Sent2vecModel()
    sent2vec_model.load_model(trained_model_path)

    if dir_name[-1] != "/":  dir_name += "/"
    os.listdir(dir_name)
    for name in os.listdir(dir_name):
        if '.' in name: continue
        out_path = args.out
        dotfiles = glob.glob(f'{dir_name}{name}/*.dot')
        out_path += f"/{name}/" if out_path[-1] != "/" else f"{name}/"
        if not os.path.exists(out_path):
            os.makedirs(out_path)
        existing_files = glob.glob(out_path + "/*.pkl")
        existing_files = [f.split('.pkl')[0] for f in existing_files]
        pool = Pool(10)
        pool.map(partial(write_to_pkl, out=out_path, existing_files=existing_files), dotfiles)


    sent2vec_model.release_shared_mem(trained_model_path)



if __name__ == '__main__':
    main()

