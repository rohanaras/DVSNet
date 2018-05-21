def generate_test_img_list(list_test):
    datadir = '/home/rohana/.kaggle/competitions/cvpr-2018-autonomous-driving/'
    list_test_map = 'md5_mapping_' + list_test
    list_test_name = list_test.split('.')[0]

    list_test = open(datadir + 'list_test/' + list_test, 'r')
    list_test_map = open(datadir + 'list_test_mapping/' + list_test_map, 'r')

    test_file_dict = {}
    for line in list_test_map:
        value_key = line.strip().split('\t')
        test_file_dict[value_key[1]] = value_key[0]

    out = open(list_test_name + 'img_list.txt', 'w')
    for line in list_test:
        key = line.strip()
        out.write(test_file_dict[key] + '.jpg\n')

if __name__ == '__main__':
    generate_test_img_list('road01_cam_5_video_1_image_list_test.txt')