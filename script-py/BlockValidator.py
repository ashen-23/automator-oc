'''
@Description: 检测项目中的内部使用了 self 的 block。
@Author: ashen23
LastEditors: ashen_23
LastEditTime: 2020-09-02 09:10:22
'''
import os, re, sys


######### 更新记录 #########
# 2020-09-02
# 1. 高亮使用了 self 的行
# 2. 增加 block 中 slef 的检测条件


###########################

# 若未指定路径，则在当前 shell 所在路径检查

# 思路
## 1. 查找所有带 ^ 的字符
## 2. 读取整个函数（或赋值代码）
## 3. 过滤掉不需要的函数(animation,masonry)
## 3. 判断是否包含 self
## 4. 高亮输入到控制台，并生成报告文件


ignoreSubfix = [
    ".xcodeproj",
    ".xcworkspace",
    ".lproj",
    ".git",
    ".xcassets",
    ".framework",
    ".bundle",
    "Pods"
]

ignoreFuncs = [
    "UIView animateWithDuration:",
    "UIView performWithoutAnimation",
    "mas_makeConstraints:",
    "mas_updateConstraints",
    "mas_remakeConstraints",
    "[TZImageManager manager]"
]
# 类型： = ^ {   或 = ^ (...) {}
patternBlockSetter = "=\\s*\\^\\s*\\([\\s\\S]*?\\)\\s*\\{|(=\\s*\\^\\s*\\s*\\{)"

# 类型：[self 或 self.
patternSelf = "\\[\\s*self\\s*|(\\s*self\\.)"

# 待解析的文件
parseFiles = []

## 判断文件夹是否需要忽略
def isNeedIgnore(path):
    return len(list(filter(lambda x:path.endswith(x), ignoreSubfix)))>0

# 定义栈
class Stack:
    def __init__(self):
        self.array = []
    
    def push(self, char):
        self.array.append(char)
    
    def pop(self):
        if self.count() > 0:
            self.array.pop()

    def count(self):
        return len(self.array)

    def isEmpty(self):
        return self.count() <= 0

    def clear(self):
        self.array = []
        

## 解析文件夹内容
def parseDir(dirName):
    dirName = dirName.strip(" ")
    if not os.path.exists(dirName):
        print("您输入的地址不正确，请检查后重试")
    if not os.path.isdir(dirName):
        parseFiles.append(dirName)
        return
    if not dirName.endswith("/"):
        dirName += "/"
    dirs = os.listdir(dirName)
    for file in dirs:
        realPath = dirName + file
        if os.path.isdir(realPath):
            if not isNeedIgnore(realPath):
                parseDir(realPath + "/")
        else:
            if realPath.endswith(".m"):
                parseFiles.append(realPath)


# block 查询器
class BlockFinder:
    def __init__(self, fileName):
        self.filename = fileName
        self.stack = Stack()
        self.blockFuncs = []
        with open(fileName, "r") as f:
            self.lines = f.readlines()
            self.text = "".join(self.lines)
            if self.text.find("^") == -1: # 不包含 block
                self.hasBlock = False
                return
            self.hasBlock = True
            self.linesNo = [0]
            for line in self.lines:
                self.linesNo.append(len(line) + self.linesNo[-1])

    # 开始搜索
    def search(self):
        self.checkSetBlock()
        self.findFunc()

    # 检查当前 block 是否包含 self
    def blockHasSelf(self, blockStart, blockEnd, blockDot):
        blockValue = self.text[blockDot:blockEnd]
        selfLines = re.finditer(patternSelf, blockValue)
        res = [(line.span()[0] + blockStart,line.span()[1] + blockStart) for line in selfLines]
        return res


    # 过滤不关心的函数
    def isIgnoreFunc(self, content):
        return len(list(filter(lambda x:x in content, ignoreFuncs)))>0

    # 获取索引所在的行数
    def _numberOfLine(self, index):
        idx = 0
        for number in self.linesNo:
            if index <= number:
                return idx
            idx += 1
        return 0

    # 是否有 block
    def isHasBlock(self):
        return self.hasBlock

    # block 的开始点
    def checkFuncStart(self, startIdx, blockIdx):
        stack = Stack()
        prefixs = self.text[startIdx:blockIdx][::-1]
        index1 = 0
        for char in prefixs:
            if char == "]":
                stack.push(char)
            elif char == "[":
                if stack.isEmpty():
                    return blockIdx - index1 - 1
                else:
                    stack.pop()            
            index1 += 1
        return -1

    # 查找函数的结束点
    def checkFuncEnd(self, blockIdx):
        stack = Stack()
        stack.push("[")
        subfix = self.text[blockIdx:]
        index2 = 0
        for char in subfix:
            if char == "[":
                stack.push(char)
            elif char == "]":
                stack.pop()
                if stack.isEmpty():
                    return blockIdx + index2 + 2 # 加2 为了获取分号
            index2 += 1
        return len(self.text)

    # block 的结束点
    def checkBlockEnd(self, blockIdx, endIdx):
        stack = Stack()
        subfix = self.text[blockIdx:endIdx]
        index = 0
        for char in subfix:
            if char == "{":
                stack.push(char)
            elif char == "}":
                stack.pop()
                if stack.isEmpty():
                    return blockIdx + index + 1
            index += 1
        return endIdx

    # 查询带 block 的函数
    def findFunc(self, start=0):
        blockIdx = self.text.find("^", start)
        if blockIdx == -1:
            return

        startIdx = self.checkFuncStart(start, blockIdx)
        # 不是函数,或者是 ignore 函数，忽略此次 block
        if startIdx == -1 or self.isIgnoreFunc(self.text[startIdx:blockIdx]): 
            self.findFunc(blockIdx+1)
            return
        endIdx = self.checkFuncEnd(blockIdx)
        line = self._numberOfLine(blockIdx)
        self.blockFuncs.append({"start": startIdx, "line": line, "end": endIdx, "blocks": []})
        self.checkFuncBlock(startIdx, endIdx)

        if endIdx >= len(self.text):
            return
        self.findFunc(endIdx+1)
    
    # 检查赋值中的 block
    def checkSetBlock(self):
        setBlocks = re.finditer(patternBlockSetter, self.text)
        for block in setBlocks:
            startIdx = block.span()[0]
            endIdx = self.checkBlockEnd(startIdx, len(self.text))
            matchBlocks = self.blockHasSelf(startIdx, endIdx, startIdx)
            if len(matchBlocks) > 0:
                line = self._numberOfLine(startIdx)
                self.blockFuncs.append({"start":self.linesNo[line-1], "line":line, "end":endIdx+1, "blocks": [{"start": startIdx, "end": endIdx, "warning": matchBlocks}]})

    # 查询函数中所有的 block
    def checkFuncBlock(self, startIdx, endIdx):
        blockIdx = self.text.find("^", startIdx, endIdx)
        if blockIdx == -1: # 没有 block 直接返回
            return
        
        blockEndIdx = self.checkBlockEnd(blockIdx, endIdx)
        # print("block 内容: {}".format(self.text[blockIdx:blockEndIdx]))
        matchBlocks = self.blockHasSelf(startIdx, endIdx, blockIdx)
        if len(matchBlocks) > 0:
            self.blockFuncs[-1]["blocks"].append({"start": blockIdx, "end": blockEndIdx,"warning": matchBlocks})

        if blockEndIdx >= endIdx: # 已查询到函数末尾
            return
        self.checkFuncBlock(blockEndIdx + 1, endIdx)
    
    # 打印结果
    def makeup(self):
        desc = ""
        count = 0
        hasLogFile = False
        for func in self.blockFuncs:
            if len(func["blocks"]) <=0:
                continue
            desc = "文件名: " + self.filename
            funcDesc = self.text[func["start"]:func["end"]]
            count += len(func["blocks"])
            for block in func["blocks"]:
                blockDesc = self.text[block["start"]:block["end"]]
                # 代码着色-block
                funcDesc = funcDesc.replace(blockDesc, "\033[33m{}\033[0m".format(blockDesc))
                # 代码着色-警告
                for errorBlock in block["warning"]:
                    lineNo = self._numberOfLine(errorBlock[0]) - 1
                    blockDesc = self.lines[lineNo]
                    funcDesc = funcDesc.replace(blockDesc, "\033[0m\033[31m{}\033[00m\033[33m".format(blockDesc))

            if not hasLogFile:
                print(desc)
                hasLogFile = True
            print("行号: {}\n{}\n".format(func["line"], funcDesc))
            # 保存文件时，取消着色
            code = funcDesc.replace("\033[33m", "").replace("\033[0m","").replace("\033[31m", "\n" + "-"*10 + "\n").replace("\033[00m", "\n" + "-"*15 + "\n")
            desc += "\n行号: {}\n{}\n\n".format(func["line"], code)        
        return (desc, count)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        path = "."
    else:
        path = sys.argv[1]
    parseDir(path)

    consoleDesc = "🎉￼￼￼🎉🎉￼￼￼🎉\n搜索路径: {}\n共分析 {} 个 .m 文件".format(path.strip(" "),len(parseFiles))
    blockFileCount = 0
    blockWarnCount = 0

    result = []
    for file in parseFiles:
        finder = BlockFinder(file)
        if not finder.isHasBlock():
            continue
        blockFileCount += 1
        finder.search()
        desc = finder.makeup()
        if desc[1] > 0:
            blockWarnCount += desc[1]
            result.append(desc[0])
    
    # 描述结果
    consoleDesc += "\n带 block 文件数: {}\n需排查 block 数: {}\n\n".format(blockFileCount, blockWarnCount)

    result.insert(0, consoleDesc)
    content = "\n\n\n\n".join(result)
    newPath = os.path.join(os.path.expanduser("~"), 'Desktop') + "/blockReport.txt"
    with open(newPath, "w+") as f:
        f.write(content)

    print("\033[32m{}\033[0m".format(consoleDesc))