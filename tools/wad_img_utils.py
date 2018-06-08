from os import listdir
from os.path import isfile, join

def generate_img_lists(kaggle_data_loc):

    list_test_path = join(kaggle_data_loc, 'list_test')
    list_test_all = [f for f in listdir(list_test_path) if isfile(join(list_test_path, f))]

    train_list_path = join(kaggle_data_loc, 'train_video_list')
    train_list_all = [f for f in listdir(train_list_path) if isfile(join(train_list_path, f))]

    for list_test in list_test_all:
        list_test_map = 'md5_mapping_' + list_test
        list_test_name = list_test.split('.')[0]

        list_test = open(join(kaggle_data_loc, 'list_test/' + list_test), 'r')
        list_test_map = open(join(kaggle_data_loc, 'list_test_mapping/' + list_test_map), 'r')

        test_file_dict = {}
        for line in list_test_map:
            value_key = line.strip().split('\t')
            test_file_dict[value_key[1]] = value_key[0]

        out = open('../list/wad_test/' + list_test_name + '_img_list.txt', 'w')
        for line in list_test:
            key = line.strip()
            out.write(test_file_dict[key] + '.jpg\n')

    for train_list in train_list_all:
        train_list_name = train_list.split('.')[0]
        out = open('../list/wad_train/' + train_list_name + '_img_list.txt', 'w')

        train_list = open(join(kaggle_data_loc, 'train_video_list/' + train_list), 'r')
        for line in train_list:
            img_path = line.split('\t')[0].split('\\')[-1]
            out.write(img_path + '\n')


if __name__ == '__main__':
    generate_img_lists('/home/rohana/.kaggle/competitions/cvpr-2018-autonomous-driving/')
