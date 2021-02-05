'''
Description: 检测项目中分类名或分类方法重名
Author: ashen23
LastEditors: ashen_23
LastEditTime: 2021-02-01 09:16:00
'''
import sys, os, re, copy, time

# 项目路径
projectPath = ""
# 分类的信息
categoryFiles = {}
# "ClassName": {"categories": {"categoryName": {"methodName": No.}}, "paths":[]}
# 记录日志信息
verboseInfos = []
errorInfos = [] # 错误信息需要放在脚本最后执行

# 查找分类的正则
reKey = "@implementation\\s*?[0-9A-Za-z_]+?\\s*?\\(\\s*?[0-9A-Za-z_]+?\\s*?\\)[\\s\\S]*?@end"
# 多行注释的正则/**/
noteKey = "/\\*([\\s\\S]*?)\\*/"
bracketKey = "\\(([\\s\\S]*?)\\)"

# 是否显示详情
isShowVerbose = False

############### 日志相关  ###############
# 绿色
def highlight(text):
    return '\033[32m{}\033[0m'.format(text)

def highlightPrint(text):
    verboseInfos.append(text)
    print(highlight(text))

# 黄色
def warning(text):
    return '\033[33m{}\033[0m'.format(text)

def warningPrint(text):
    verboseInfos.append(text)
    print(warning(text))

# 红色
def errorText(text):
    return '\033[31m{}\033[0m'.format(text)

def errorTextPrint(text, appended=True):
    if appended:
        verboseInfos.append(text)
    if text.startswith("--WARNING--"):
        print(warning(text[11:]))
    else:
        print(errorText(text))

# 自定义日志输出
def cusPrint(text, mode,isForce=False):
    global isShowVerbose
    if not isShowVerbose and not isForce:
        verboseInfos.append(text)
        return
    if mode == 1:
        highlightPrint(text)
    elif mode == 2:
        warningPrint(text)
    elif mode == 3:
        errorTextPrint(text)
    else:
        verboseInfos.append(text)
        print(text)

def logWrite2File():
    # 日志写入文件
    global errorInfos
    global verboseInfos
    curTime = time.strftime("%Y-%m-%d-%H:%M:%S", time.localtime())
    newPath = os.path.join(os.path.expanduser("~"), 'Desktop') + "/CategoryChecker_{}.txt".format(curTime)
    
    # 处理文本
    idx = verboseInfos.index("--RESPONSE--")
    infos = verboseInfos[:idx] + errorInfos + verboseInfos[idx+1:]
    
    results = "\n".join(infos).replace("--WARNING--", "")
    results = results.replace("\033[31m", "").replace("\033[33m", "").replace("\033[32m", "").replace("\033[0m","")
    with open(newPath, "w") as f:
        f.write(results)
######################################


############### 判断 ################
def isCodeFile(pathname):
    return pathname.endswith(".m")

def getClassAndCategoryName(pathname):
    return pathname.split("/")[-1].split("+")

# 删除连续的空格
def dropContinueSpace(spaceStr):
    spaceStr = spaceStr.strip()
    while True:
        tmp = spaceStr.replace("  ", " ")
        if len(tmp) == len(spaceStr):
            return tmp
        spaceStr = tmp

######################################
# 生成函数签名
def makeMethodSign(funcStr):
    filterStr = funcStr.replace("\n", "").replace("{","")
    # 去除参数类型
    paramTypes = re.findall(bracketKey, filterStr)
    for paramType in paramTypes:
        filterStr = filterStr.replace(paramType, "")
    filterStr = dropContinueSpace(filterStr.replace("(","").replace(")","")).replace(" :", ":")

    # 没有参数直接返回
    if not ":" in filterStr:
        return filterStr.replace(" ", "")

    strs = filterStr.split(" ")
    return filterStr[0] + ":".join([x.split(":")[0] for x in strs if ":" in x]) + ":"

# 判断重复的函数签名
def judgeDuplication():
    global categoryFiles
    global errorInfos
    duplicateInfo = []
    
    cateCount = 0
    methodCount = 0
    for key,category in categoryFiles.items():
        cached = []
        cateCount += len(category["categories"])
        for cateKey,methods in category["categories"].items():
            methodCount += len(methods)

            # 判断函数签名重复
            for cateKey2,methods2 in category["categories"].items():
                if cateKey != cateKey2:
                    for method in methods:
                        cacheKey = key + "+" + method
                        if method in methods2 and cacheKey not in cached:
                            cached.append(cacheKey)
                            duplicateInfo.append("No.{} {} in {}({},{})".format(methods[method], method, key,cateKey,cateKey2))

    # 输出信息
    cateDesc = warning(cateCount) + highlight(" 个分类，") + warning(methodCount) + highlight("个方法。")
    response1 = highlight("\t解析完毕。") + warning(len(categoryFiles)) + highlight(" 个类中存在 ") + cateDesc
    response2 = "\t" + warning(max(len(errorInfos)-2,0)) + errorText(" 处分类名冲突，") + warning(len(duplicateInfo)) + errorText(" 处分类方法冲突。")
    for clsName,category in categoryFiles.items():
        cusPrint("类名: " + warning(clsName), 0)
        for cateKey,methods in category["categories"].items():
            cusPrint("\t分类名: {}\n\t分类函数签名 \n\t\t{}\n".format(warning(cateKey),warning("\n\t\t".join(methods))), 0)
    if len(duplicateInfo) > 0:
        errorInfos.append("\n")
        errorInfos.append("--WARNING--分类函数签名冲突: ")
        for dup in duplicateInfo:
            errorInfos.append("\t" + dup)

    for error in errorInfos:
        errorTextPrint(error,appended=False)
    
    verboseInfos.append("--RESPONSE--")
    header = "\n" + "*"*21 + " 🎉🎉🎉 " + "*"*20
    highlightPrint(header)

    cusPrint("",0,True)
    cusPrint(response1,0,True)
    cusPrint(response2, 1, True)
    cusPrint("",0,True)

    if len(duplicateInfo) == 0:
        highlightPrint("\n\tCongratulations，分类中暂未查询到重复的方法签名")
    highlightPrint(header)


# 查询当前分类的所有方法签名
def lookupMethods(funcStr,contents,methods):
    lines = funcStr.split("\n")
    startIdx = -1
    for idx,line in enumerate(lines):
        if len(line) > 0:
            line = line.strip("\n")
            if line.startswith("-") or line.startswith("+") or line.startswith("@property"):
                startIdx = idx
            if line.endswith("{") and not line.startswith("//") and startIdx != -1:
                signMethodStr = makeMethodSign("\n".join(lines[startIdx:idx+1]))
                lineNo = contents.index(line) + 1
                if signMethodStr not in methods:
                    methods[signMethodStr] = lineNo
                startIdx = -1

# 从正则中获取类名和分类名
def fetchClassName(name,span):
    global errorInfos
    names = dropContinueSpace(span.split("\n")[0].replace("@implementation", "")).strip()
    leftIdx = names.find("(")
    rightIdx = names.find(")")
    if leftIdx == -1 or rightIdx == -1:
        if not isShowVerbose:
            errorInfos.append("\n\t{}".format(name))
        errorInfos.append("\t\t当前文件格式不规范，请检查. @implementation 和(分类名)不在同一行")
    cateName = names[leftIdx+1:rightIdx].strip()
    return (names[:leftIdx].strip(), cateName)


# 解析分类文件
def parseCodeFiles():
    global categoryFiles
    global isShowVerbose
    global errorInfos
    cusPrint("解析分类：",2)

    cachedMap = copy.deepcopy(categoryFiles)
    for _,category in categoryFiles.items():
        for path in category["paths"]:
            name = "+".join(getClassAndCategoryName(path))
            cusPrint("\t{}".format(name),2)
            with open(path, "r") as f:
                content = f.read()
                contents = content.split("\n")
                spans = re.findall(reKey, content)
                if not spans or len(spans) == 0:
                    if not isShowVerbose:
                        errorInfos.append("\t{}".format(name))
                    continue
                
                for funcStr in spans:
                    # 获取当前类名,防止分类中存放了其他类的分类
                    clsName = fetchClassName(name,funcStr)
                    newKey = clsName[0]
                    cateKey = clsName[1]
                    if newKey not in cachedMap:
                        cachedMap[newKey] = {"paths": category["paths"], "categories":{cateKey: {}}}
                    
                    noteSpans = re.findall(noteKey, funcStr) # 排除注释的干扰
                    if len(noteSpans) > 0:
                        for noteSpan in noteSpans:
                            funcStr = funcStr.replace(noteSpan, "").replace("/**/","")
                    if not cateKey in cachedMap[newKey]["categories"]:
                        cachedMap[newKey]["categories"][cateKey] = {}
                    lookupMethods(funcStr, contents, cachedMap[newKey]["categories"][cateKey])
    # 过滤空数据
    for k,v in cachedMap.items():
        emptyKey = []
        for cateKey,methods in v["categories"].items():
            if len(methods) == 0:
                emptyKey.append(cateKey)
        for k in emptyKey:
            v["categories"].pop(k)   
    categoryFiles = cachedMap
    
# 解析当前文件所有的分类
def searchCategories():
    global projectPath
    global categoryFiles
    global errorInfos

    # 以 类名+categoryName 为 key 存储数据
    # 获取当前所有组件
    for path,_,paths in os.walk(projectPath):
        for name in paths:
            if "+" in name and isCodeFile(name):
                realName = os.path.splitext(name.replace(" ", ""))[0]
                splitFile = getClassAndCategoryName(realName)
                clsName = splitFile[0]
                cateName = splitFile[1]
                nagitivePath = path+"/"+name
                if clsName in categoryFiles:
                    if cateName in categoryFiles[clsName]["categories"]:
                        allName = clsName+"+"+cateName
                        # 尝试获取冲突的另外一个文件名
                        dupPath = ""
                        for apath in categoryFiles[clsName]["paths"]:
                            if allName in apath:
                                dupPath = apath
                        if len(errorInfos) == 0:
                            errorInfos.append("\n")
                            errorInfos.append("--WARNING--分类名冲突:")
                        errorInfos.append("\n\t'{}' duplicated. in \n\t\t{}".format(allName,nagitivePath) + "\n\t\t" + dupPath)
                    else:
                        categoryFiles[clsName]["categories"][cateName] = {}
                    categoryFiles[clsName]["paths"].append(nagitivePath)
                else:
                    categoryFiles[clsName] = {"paths": [nagitivePath], "categories":{cateName: {}}}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        projectPath = input(highlight("请输入查询的代码路径："))
    else:
        projectPath = sys.argv[1]

    if "--verbose" in sys.argv:
        isShowVerbose = True

    startInfo = "\n\n" + "#"*20 + "开始分析" + "#"*20
    startInfo += "\n\n\t- 添加 --verbose 参数可查看详情\n\t- 解析日志存在桌面文件 CategoryChecker***.txt"
    startInfo += "\n\n" + "#"*50
    warningPrint(startInfo)

    # 查询所有分类
    searchCategories()

    parseCodeFiles()

    judgeDuplication()

    logWrite2File()

    warningPrint("\n\n" + "#"*20 + "分析结束" + "#"*20 + "\n\n")