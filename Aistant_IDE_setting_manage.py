
import json
import os
class Aistant_Agent_Setting():
    def __init__(self, name = 'Agent_0'):
        print("Aistant_Setting init.")

        self.aistant_ide_agent_name = name
        
        self.aistant_ide_function_prompt = 'Hello'

        self.aistant_ide_model_index = 0

        self.aistant_ide_tempeture = 0.7

        self.aistant_ide_max_token = 150

        self.aistant_ide_extern_link = '' 

        self.aistant_ide_tempory_output_content = ''

        self.aistant_ide_run_handle = None

# UI option complete list 
        self.chat_model_dict = [
        {'company':'openai', 'model':'gpt-3.5-turbo', 'type': 'Chat'},
        {'company':'openai', 'model':'gpt-3.5-turbo-0301', 'type': 'Chat'},
        {'company':'openai', 'model':'text-davinci-003', 'type': 'Complete'},
        {'company':'openai', 'model':'text-curie-001', 'type': 'Complete'},
        {'company':'openai', 'model':'text-babbage-001', 'type': 'Complete'},
        {'company':'openai', 'model':'text-ada-001', 'type': 'Complete'},
        {'company':'openai', 'model':'text-davinci-002', 'type': 'Complete'},
        {'company':'openai', 'model':'text-davinci-001', 'type': 'Complete'},
        {'company':'openai', 'model':'davinci-instruct-beta', 'type': 'Complete'},
        {'company':'openai', 'model':'davinci', 'type': 'Complete'},
        {'company':'openai', 'model':'curie-instruct-beta', 'type': 'Complete'},
        {'company':'openai', 'model':'curie', 'type': 'Complete'},
        {'company':'openai', 'model':'babbage', 'type': 'Complete'},
        {'company':'openai', 'model':'ada', 'type': 'Complete'}, 
        ]


# default agent setting
        self.aistant_ide_agent_json_default_content  =   {
                                                'name': 'Agent',
                                                'function_prompt': 'Hello',
                                                'model': 0,
                                                'tempeture': 0.7,
                                                'max_token': 150,
                                                'extern_link': '',
                                                }

# local save manage
        self.aistant_setting_file_path = 'setting_' + self.aistant_ide_agent_name + '.json'
        self.aistant_check_local_setting_and_update_cache()

# Detect and update setting file when software starts
    def aistant_check_local_setting_and_update_cache(self):
        content = self.aistant_get_content_by_json_file()
        # TODO: 增加必要的合法性检查, 比如key少的情况下，需要与默认配置进行合并补全
        if content == '':
            self.aistant_recover_with_default_setting()
            return
        self.aistant_json_tempory_content = content

# get content of setting.json
    def aistant_get_content_by_json_file(self):
        content = ''
        if os.path.isfile(self.aistant_setting_file_path):
            print("Setting file exists.")
            with open(self.aistant_setting_file_path, 'r') as f:
                try:
                    content = json.load(f)
                except ValueError as e:
                    print("Setting file is not a valid json file. Recover to default setting.")
        else:
            print("Setting file does not exist. Recover to default setting.")
        return content

# recover setting.json to default setting
    def aistant_recover_with_default_setting(self):
        print("aistant_recover_with_default_setting")
        with open(self.aistant_setting_file_path, 'w') as f:
            json.dump(self.aistant_ide_agent_json_default_content, f)
        self.aistant_json_tempory_content = self.aistant_ide_agent_json_default_content

    def aistant_update_local_file_with_content(self):
        print("aistant_update_local_file_with_content")
        with open(self.aistant_setting_file_path, 'w') as f:
            json.dump(self.aistant_json_tempory_content, f)

# --------------Access (read/write) related methods of local setting ------------------#
# single agent setting
    def aistant_setting_get_model_id(self):
        try:
            model_val = self.aistant_json_tempory_content['model']
        except:
            model_val = -1
        return model_val
    
    def aistant_setting_set_model_id(self, model_id):
        ret = 0
        try:
            self.aistant_json_tempory_content['model'] = model_id
        except:
            self.aistant_json_tempory_content['model'] = 0
            ret = -1
        self.aistant_update_local_file_with_content()
        return ret
    
    def aistant_setting_get_tempeture(self):
        try:
            temp_val = self.aistant_json_tempory_content['tempeture']
        except:
            temp_val = 0.7
        return temp_val
    
    def aistant_setting_set_tempeture(self, temp_val):
        ret = 0
        try:
            self.aistant_json_tempory_content['tempeture'] = temp_val
        except:
            self.aistant_json_tempory_content['tempeture'] = 0.7
            ret = -1
        self.aistant_update_local_file_with_content()
        return ret
    
    def aistant_setting_get_max_token(self):
        try:
            max_token_val = self.aistant_json_tempory_content['max_token']
        except:
            max_token_val = 150
        return max_token_val
    
    def aistant_setting_set_max_token(self, max_token_val):
        ret = 0
        try:
            self.aistant_json_tempory_content['max_token'] = max_token_val
        except:
            self.aistant_json_tempory_content['max_token'] = 150
            ret = -1
        self.aistant_update_local_file_with_content()
        return ret
    
    def aistant_setting_get_extern_link(self):
        try:
            extern_link_val = self.aistant_json_tempory_content['extern_link']
        except:
            extern_link_val = ''
        return extern_link_val
    
    def aistant_setting_set_extern_link(self, extern_link_val):
        ret = 0
        try:
            self.aistant_json_tempory_content['extern_link'] = extern_link_val
        except:
            self.aistant_json_tempory_content['extern_link'] = ''
            ret = -1
        self.aistant_update_local_file_with_content()
        return ret
    
    def aistant_setting_get_agent_name(self):
        try:
            agent_name_val = self.aistant_json_tempory_content['agent_name']
        except:
            agent_name_val = 'Agent'
        return agent_name_val
    
    def aistant_setting_set_agent_name(self, agent_name_val):
        ret = 0
        try:
            self.aistant_json_tempory_content['agent_name'] = agent_name_val
        except:
            self.aistant_json_tempory_content['agent_name'] = 'Agent'
            ret = -1
        self.aistant_update_local_file_with_content()
        return ret

    def aistant_setting_get_function_prompt(self):
        try:
            function_prompt_val = self.aistant_json_tempory_content['function_prompt']
        except:
            function_prompt_val = 'Hello'
        return function_prompt_val
    
    def aistant_setting_set_function_prompt(self, function_prompt_val):
        ret = 0
        try:
            self.aistant_json_tempory_content['function_prompt'] = function_prompt_val
        except:
            self.aistant_json_tempory_content['function_prompt'] = 'Hello'
            ret = -1
        self.aistant_update_local_file_with_content()
        return ret


#  UI元素补全

    def aistant_chat_model_dict_get_config(self):
        return self.chat_model_dict
    
    def aistant_chat_model_dict_get_idx_by_model(self, model):
        for idx, model_name in enumerate(self.chat_model_dict):
            print(idx, model_name)
            if model_name['model'] == model:
                return idx

# ========================= Public Setting =========================#

class Aistant_Public_Setting():
    def __init__(self):
        self.aistant_public_setting_file_path = 'aistant_public_setting.json'
        self.aistant_public_setting_json_default_content = {
            "cur_key_value": ""
        }

        self.aistant_public_check_local_setting_and_update_cache()

    def aistant_public_check_local_setting_and_update_cache(self):
        content = self.aistant_public_get_content_by_json_file()
        if content == '':
            self.aistant_public_recover_with_default_setting()
            return
        self.aistant_public_json_tempory_content = content

    def aistant_public_get_content_by_json_file(self):
        content = ''
        if os.path.isfile(self.aistant_public_setting_file_path):
            print("Setting file exist")
            with open(self.aistant_public_setting_file_path, 'r') as f:
                try:
                    content = json.load(f)
                except ValueError as e:
                    print("Setting file is invalid, recover to default")
        else:
            print("Setting file not exist. Recover to default")
        return content


    def aistant_public_recover_with_default_setting(self):
        print("aistant_public_recover_with_default_setting")
        with open(self.aistant_public_setting_file_path, 'w') as f:
            json.dump(self.aistant_public_setting_json_default_content, f)
        self.aistant_public_json_tempory_content = self.aistant_public_setting_json_default_content

    def aistant_public_update_local_file_with_content(self):
        with open(self.aistant_public_setting_file_path, 'w') as f:
            json.dump(self.aistant_public_json_tempory_content, f)

# public setting
    def aistant_setting_public_get_cur_key_val(self):
        try:
            cur_key_val = self.aistant_public_json_tempory_content['cur_key_value']
        except KeyError:
            print("aistant_setting_public_get_cur_key_val. Empty.")
            cur_key_val = ''
        return cur_key_val
    
    def aistant_setting_public_set_cur_key_val(self, key_val):
        ret = 0
        try:
            print("aistant_setting_public_set_cur_key_val: ", key_val)
            self.aistant_public_json_tempory_content['cur_key_value'] = key_val
        except:
            print("aistant_setting_public_set_cur_key_val. Empty.")
            self.aistant_public_json_tempory_content['cur_key_value'] = ''
            ret = -1
        self.aistant_public_update_local_file_with_content()
        return ret

    def aistant_public_update_local_file_with_content(self):
        with open(self.aistant_public_setting_file_path, 'w') as f:
            json.dump(self.aistant_public_json_tempory_content, f)



if __name__ == "__main__":
    print("Aistant setting manage")
    aistant_setting = Aistant_Agent_Setting()