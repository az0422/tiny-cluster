def parser(args):
    args_list = []
    args_dict = {}

    key = None
    for arg in args[1:]:
        if arg.startswith("-"):
            args_dict[arg] = True
            key = arg

        else:
            if key is not None:
                args_dict[key] = arg
                key = None

            else:
                args_list.append(arg)
    
    return args_list, args_dict

def args_checker(args_dict, args_keys):
    flag = True
    invalid = None

    for key in args_dict.keys():
        if key in args_keys:
            continue
        flag = False
        invalid = key
        break
    
    return flag, invalid