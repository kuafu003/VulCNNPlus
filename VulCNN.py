import argparse, os
from model import load_data, CNN_Classifier

def parse_options():
    parser = argparse.ArgumentParser(description='VulCNN training.')
    parser.add_argument('-i', '--input', help='The dir path of train.pkl and test.pkl', type=str, required=True)
    parser.add_argument('-d', '--dataset', help='nobalance dataset',default=False, action='store_true')
    parser.add_argument('-s', '--save', help='result save path', type=str)
    args = parser.parse_args()
    return args

def get_kfold_dataframe(pathname = "./data/", item_num = 0):
    pathname = pathname + "/" if pathname[-1] != "/" else pathname
    train_df = load_data(pathname + "train.pkl")[item_num]
    eval_df = load_data(pathname + "test.pkl")[item_num]
    # test_df = eval_df.copy(deep=True) 
    return train_df, eval_df

def main():
    args = parse_options()
    item_num = 0
    hidden_size = 128
    data_path = args.input
    result_save_path = args.save if args.save else data_path.replace("pkl", "results")
    if args.dataset:
        for item_num in range(5):
            data_path = data_path + "/" if data_path[-1] != "/" else data_path
            train_df = load_data(data_path + "train.pkl")
            eval_df = load_data(data_path + "valid.pkl")
            test_df = load_data(data_path + "test.pkl")
            classifier = CNN_Classifier(result_save_path = result_save_path, \
                    item_num = item_num, epochs=20, hidden_size = hidden_size)
            classifier.preparation(
                X_train=train_df['data'],
                y_train=train_df['label'],
                X_valid=eval_df['data'],
                y_valid=eval_df['label'],
                X_test=test_df['data'],
                y_test=test_df['label']
            )
            classifier.train()
    else:
        for item_num in range(5):
            train_df, eval_df = get_kfold_dataframe(pathname = data_path, item_num = item_num)
            classifier = CNN_Classifier(result_save_path = result_save_path, \
                item_num = item_num, epochs=200, hidden_size = hidden_size)
            classifier.preparation(
                X_train=train_df['data'],
                y_train=train_df['label'],
                X_valid=eval_df['data'],
                y_valid=eval_df['label'],
            )
            classifier.train()


if __name__ == "__main__":
    main()