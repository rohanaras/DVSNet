def generate_test_img_lists(kaggle_data_loc):
    from os import listdir
    from os.path import isfile, join

    list_test_path = join(kaggle_data_loc, 'list_test')
    list_test_all = [f for f in listdir(list_test_path) if isfile(join(list_test_path, f))]

    for list_test in list_test_all:
        list_test_map = 'md5_mapping_' + list_test
        list_test_name = list_test.split('.')[0]

        list_test = open(kaggle_data_loc + 'list_test/' + list_test, 'r')
        list_test_map = open(kaggle_data_loc + 'list_test_mapping/' + list_test_map, 'r')

        test_file_dict = {}
        for line in list_test_map:
            value_key = line.strip().split('\t')
            test_file_dict[value_key[1]] = value_key[0]

        out = open('../list/wad_test/' + list_test_name + '_img_list.txt', 'w')
        for line in list_test:
            key = line.strip()
            out.write(test_file_dict[key] + '.jpg\n')


if __name__ == '__main__':
    generate_test_img_lists('/home/rohana/.kaggle/competitions/cvpr-2018-autonomous-driving/')
