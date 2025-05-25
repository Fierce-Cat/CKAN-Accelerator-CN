# Convert original ckan download link to kerbcat link
# -*- coding: utf-8 -*-

import json
import re
import os
import time
import uuid
# import subprocess # Not strictly needed if git operations are removed from this script
from hashlib import md5
from pathlib import Path
import argparse # For command-line arguments

def getFolder(p): #获取p路径下所有文件夹路径
    return [x for x in p.iterdir() if x.is_dir()]

# def getFile(p): #获取p路径下所有文件路径 # Not used in the provided main logic
#     return [x for x in p.iterdir() if not x.is_dir()]

def getCkanFile(p): #获取.ckan文件路径
    ckanlist=[x for x in p.iterdir() if not x.is_dir()]
    return [ckanfile for ckanfile in ckanlist if '.ckan' in ckanfile.suffix] # Fixed to check suffix properly

def is_oldver(jsonfile):
    try:
        if jsonfile['ksp_version']=='any':
            return False
        else:
            if isVersionGreater('1.7.0',jsonfile['ksp_version']):
                return True
            else:
                return False
    except KeyError:
        try:
            if isVersionGreater('1.7.0',jsonfile['ksp_version_max']):
                return True
            else:
                return False
        except KeyError:
            return False

#left版本是否大于right版本
def isVersionGreater(left,right):
    #版本正则
    vre=r"^(?:(?P<epoch>[0-9]+):)?v?(?P<version>.*)$"
    #epoch比较
    left_match = re.match(vre,left)
    right_match = re.match(vre,right)

    if not left_match or not right_match: # Handle cases where version string might not match regex
        return False # Or raise an error, or handle as per specific needs

    leftepoch = 0
    if left_match.group('epoch') != None:
        leftepoch=int(left_match.group('epoch'))
    
    rightepoch = 0
    if right_match.group('epoch') != None:
        rightepoch=int(right_match.group('epoch'))
    
    if leftepoch<rightepoch:
        return False
    elif leftepoch>rightepoch:
        return True
    else:
        #版本号比较
        leftver=left_match.group('version').replace('-','.').split('.')
        rightver=right_match.group('version').replace('-','.').split('.')
        #获得最长版本号长度
        verlen=max(len(leftver),len(rightver))
        i=0
        #逐位比较版本号
        while i<verlen:
            try:
                #如超出索引，版本号较长的大
                if i==len(rightver):
                    return True
                elif i==len(leftver):
                    return False
                #优先尝试以整型比较
                if int(leftver[i])>int(rightver[i]):
                    return True
                elif int(leftver[i])<int(rightver[i]):
                    return False
                else:
                    i=i+1
            except ValueError:
                #如含有字符，按字符串比较
                if leftver[i]>rightver[i]:
                    return True
                elif leftver[i]<rightver[i]:
                    return False
                else:
                    i=i+1
        return False # If versions are identical

def mkdir(path):    # make local path files
    folder = os.path.exists(path)
    if not folder:                  #判断是否存在文件夹如果不存在则创建为文件夹
        os.makedirs(path)            #makedirs 创建文件时如果路径不存在会创建这个路径
    return path

def linkreplace(download, download_size):
    gre=r"^https:\/\/github\.com.*"
    sre=r"^https:\/\/spacedock\.info.*"
    sarbianre=r"^https:\/\/ksp\.sarbian\.com.*"
    size='&size=' + str(int(download_size))
    timestamp=str(int(time.time()+1.5*86400))
    exp='&expireAt=' + timestamp
    # This key is used to generate the download link signature for kerbcat.cn
    authkey = os.environ.get("CDN_KEY")
    
    def generate_kerbcat_link(original_url, domain_to_replace, kerbcat_path_prefix):
        link = original_url.replace(f"https://{domain_to_replace}", f"https://hk-github.mirror.kerbcat.cn/{kerbcat_path_prefix}")
        filename = original_url.replace(f"https://{domain_to_replace}", f'/{kerbcat_path_prefix}')
        rand = str(uuid.uuid4()).replace('-', '')
        uid = '0'
        sstring = f"{filename}-{timestamp}-{rand}-{uid}-{authkey}"
        hashvalue = md5(sstring.encode('utf-8')).hexdigest()
        return f"{link}?auth_key={timestamp}-{rand}-{uid}-{hashvalue}{size}{exp}"

    if re.match(gre,str(download)):
        return generate_kerbcat_link(download, "github.com", "github")
    if re.match(sarbianre,str(download)):
        return generate_kerbcat_link(download, "ksp.sarbian.com", "sarbian")
    return download

def detectkclink(download):
    # global linkReplaced # This global variable usage is a bit tricky; better to return a boolean
    gre=r"^https:\/\/hk-github\.mirror\.kerbcat\.cn.*"
    return re.match(gre,str(download)) is not None

def namereplace(name):
    originalname=name
    name = originalname + ' [PRO-KCMIRROR]'
    return name
    
def abstractreplace(abstract):
    originalabstract = abstract
    abstract = originalabstract + ' [All download links for this mod have been accelerated by KERBCAT.COM]'
    return abstract

# The recreate_git_branch function is defined in the original script but commented out.
# It's generally not recommended for automated GitHub Actions on main branches due to its destructive nature.
# If needed for specific scenarios, it should be handled with extreme care.
# def recreate_git_branch(branch_name):
#  """Deletes and recreates the specified Git branch. ... """
#  pass # Kept for reference from original script

if __name__=="__main__":
    parser = argparse.ArgumentParser(description="Process .ckan files to replace download links and update metadata.")
    parser.add_argument("input_dir", help="Directory containing the source .ckan files (e.g., a clone of CKAN-meta).")
    parser.add_argument("output_dir", help="Directory where processed .ckan files will be saved.")
    args = parser.parse_args()

    inputPath = Path(args.input_dir)
    outputPath = Path(args.output_dir)

    if not inputPath.is_dir():
        print(f"Error: Input directory '{inputPath}' does not exist or is not a directory.")
        exit(1)
    
    # Output path will be created by the script if it doesn't exist.

    print(f"Processing CKAN files from: {inputPath}")
    print(f"Outputting processed files to: {outputPath}")

    ckanFolderList=getFolder(inputPath)

    for ckanFolder in ckanFolderList:
        if ckanFolder.name=='.git': # Skip .git folder from source
            continue
        
        # Ensure output subfolder exists
        outputFolder = mkdir(outputPath / ckanFolder.name) # Use ckanFolder.name to keep original folder name

        ckan_files_in_folder = getCkanFile(ckanFolder)
        if not ckan_files_in_folder:
            # If the source folder has no .ckan files, we might not need to create an output folder for it
            # or we might want to remove it if it was created and remains empty later.
            # For now, mkdir creates it; the original script removes it if it stays empty.
            pass


        processed_files_in_folder = 0
        for ckanFile in ckan_files_in_folder:
            print(f"\rProcessing: {ckanFile.relative_to(inputPath)}                         ", end='')
            try:
                with open(ckanFile, encoding='utf-8') as originalFile:
                    originalJson=json.load(originalFile)
                
                if is_oldver(originalJson):
                    print(f"\rSkipping old version: {ckanFile.name} ({originalJson.get('ksp_version', 'N/A')})")
                    continue

                kcJson=json.loads(json.dumps(originalJson)) # Deep copy

                link_was_replaced = False
                if 'download' in originalJson and 'download_size' in originalJson:
                    if originalJson['download_size'] < 838860800: # 800MB limit
                        new_download_link = linkreplace(originalJson['download'], originalJson['download_size'])
                        if new_download_link != originalJson['download'] and detectkclink(new_download_link):
                            kcJson['download'] = new_download_link
                            link_was_replaced = True
                            if 'name' in kcJson: # Check if 'name' exists before trying to replace
                                kcJson['name']=namereplace(originalJson['name'])
                            if 'abstract' in kcJson: # Check if 'abstract' exists
                                kcJson['abstract']=abstractreplace(originalJson['abstract'])
                
                outputFile=outputFolder/ckanFile.name
                with open(outputFile, encoding='utf-8', mode='w') as kcFile:
                    kcFile.write(json.dumps(kcJson, sort_keys=True, indent=4, ensure_ascii=False))
                processed_files_in_folder +=1

            except json.JSONDecodeError:
                print(f"\rError decoding JSON from file: {ckanFile.name}")
            except Exception as e:
                print(f"\rAn error occurred while processing {ckanFile.name}: {e}")
        
        if processed_files_in_folder == 0 and outputFolder.exists() and not any(outputFolder.iterdir()):
            print(f"\nRemoving empty output directory: {outputFolder}")
            try:
                os.rmdir(outputFolder)
            except OSError as e:
                print(f"Could not remove directory {outputFolder}: {e}")


    print('\nFile processing complete.')
