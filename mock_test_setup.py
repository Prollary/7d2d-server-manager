import os
import shutil
import zipfile

def create_mock_data():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    test_assets_dir = os.path.join(base_dir, "Test_Assets")
    
    # 清理并创建测试资源文件夹
    if os.path.exists(test_assets_dir):
        shutil.rmtree(test_assets_dir)
    os.makedirs(test_assets_dir)
    
    print("[1/3] 正在生成测试用模组文件夹 (Mod_Folder_Test)...")
    mod_folder = os.path.join(test_assets_dir, "Mod_Folder_Test")
    os.makedirs(mod_folder)
    with open(os.path.join(mod_folder, "ModInfo.xml"), "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8" ?>\n<xml>\n    <ModInfo>\n        <Name value="FolderTestMod"/>\n        <Description value="这是一个文件夹形式测试模组"/>\n    </ModInfo>\n</xml>')
        
    print("[2/3] 正在生成测试用模组 ZIP 压缩包 (Mod_Test.zip)...")
    zip_path = os.path.join(test_assets_dir, "Mod_Test.zip")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.writestr("Mod_Test/ModInfo.xml", '<?xml version="1.0" encoding="UTF-8" ?>\n<xml>\n    <ModInfo>\n        <Name value="ZipTestMod"/>\n        <Description value="这是一个ZIP形式测试模组"/>\n    </ModInfo>\n</xml>')

    print("[3/3] 正在生成测试用地图文件夹 (MyMap)...")
    map_folder = os.path.join(test_assets_dir, "MyMap")
    os.makedirs(map_folder)
    with open(os.path.join(map_folder, "map_info.xml"), "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8" ?>\n<MapInfo>\n    <Name value="MyMap"/>\n</MapInfo>')
        
    print(f"\n✅ 所有测试文件均已生成完毕！")
    print(f"请前往 {test_assets_dir} 目录中获取您的测试文件包。")

if __name__ == "__main__":
    create_mock_data()
