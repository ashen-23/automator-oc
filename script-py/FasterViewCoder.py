'''
Description: 快速生成OC视图代码
Author: ashen23
LastEditors: ashen23
LastEditTime: 2020-06-13 11:16:00
'''

import os,sys

helpInfo = '''
\033[33m生成简易 OC 视图代码(@property, getter, AutoLayout)\033[0m

\033[33m参数描述:\033[0m
    viewName:ViewType:layoutType
    视图名称:视图类型:布局类型
    
    e.g. nameLabel:UILabel
    
    e.g. nameLabel:UILabel:e
        (e: make.edges (支持五种布局方式e/t/l/a/s), 详情可查看`内置布局`)
        
    e.g. nameLabel:l
        (l 是UILabel的简写)
        
    e.g. :l
        (省略的名称默认为类型去掉'UI'前缀,此处结果是`lable`)
        
    e.g. nameLabel:i nextButton:b numberText:t:a
        (支持同时生成生成多个视图)

\033[33m内置布局：\033[0m
    default: (left + top)
    e: edge
    t: top
    l: left
    a: all (top + left + bottom + right)
    s: size（left + top + width + height）

\033[33m自定义布局：\033[0m
    类型1,值1/类型2,值2
    e.g. w,200/h,100
        (设置布局宽度200，高度100)

    e.g. lt,20/r,15
        (设置视图左侧和顶部相对于父视图为20,右侧视图相对于父视图为15)
    
    e.g. L,20/T,15
        (设置左侧相对于上一个视图间距20，顶部视图相距于上一个视图间距15)
        (上一个视图指执行脚本时的上一个)

\033[33m其他参数：\033[0m
    -view: 视图添加在UIView上，默认添加在UIViewController上

'''

### 以下是模板

# 默认padding
paddings = '15'

viewMap = {'c': 'UICollectionView', 't':'UITableView', 'l':'UILabel', 
           'tx':'UITextField', 'tv':'UITextView', 'i':'UIImageView',
            'b':'UIButton', 'v':'UIView'}

layoutMap = {'l':'left', 'r':'right', 't':'top', 'b':'bottom','w':'width','h':'height'}

layoutRela = {'l':'right','t':'bottom','r':'left','b':'top'}

getFunc = '''
- (<#type#> *)<#name#> {
    if (!_<#name#>) {
        _<#name#> = [[<#type#> alloc] init];
        <#extension#>
    }
    return _<#name#>;
}
'''

layoutBase = '''
[<#parent#> addSubview:self.<#name#>];
[self.<#name#> mas_makeConstraints:^(MASConstraintMaker *make) {
<#layout#>
}];
'''

# 默认：左+上
layoutDefault = '''
[<#parent#> addSubview:self.<#name#>];
[self.<#name#> mas_makeConstraints:^(MASConstraintMaker *make) {
    make.left.equalTo(<#parent#>).offset(<#padding#>);
    make.top.equalTo(<#parent#>).offset(<#padding#>);
}];
'''

# edge
layoutEdge = '''
[<#parent#> addSubview:self.<#name#>];
[self.<#name#> mas_makeConstraints:^(MASConstraintMaker *make) {
    make.edges.equalTo(<#parent#>);
}];
'''

# 上左+宽高
layoutSize = '''
[<#parent#> addSubview:self.<#name#>];
[self.<#name#> mas_makeConstraints:^(MASConstraintMaker *make) {
    make.left.equalTo(<#parent#>).offset(<#padding#>);
    make.top.equalTo(<#parent#>).offset(<#padding#>);
    make.width.equalTo(<#width#>);
    make.height.equalTo(<#height#>);
}];
'''

# 上下左右
layoutAll = '''
[<#parent#> addSubview:self.<#name#>];
[self.<#name#> mas_makeConstraints:^(MASConstraintMaker *make) {
    make.left.equalTo(<#parent#>).offset(<#padding#>);
    make.top.equalTo(<#parent#>).offset(<#padding#>);
    make.right.equalTo(<#parent#>).offset(-<#padding#>);
    make.height.equalTo(<#parent#>).offset(-<#padding#>);
}];
'''

# 左侧与左面视图右侧相关
layoutL = '''
[<#parent#> addSubview:self.<#name#>];
[self.<#name#> mas_makeConstraints:^(MASConstraintMaker *make) {
    make.left.equalTo(<#last#>.mas_bottom).offset(<#padding#>);
}];
'''

# 顶部与上面视图的底部相关
layoutT = '''
[<#parent#> addSubview:self.<#name#>];
[self.<#name#> mas_makeConstraints:^(MASConstraintMaker *make) {
    make.top.equalTo(<#last#>.mas_bottom).offset(<#padding#>);
}];
'''

module_button = '''
        _<#name#> = [UIButton buttonWithType:UIButtonTypeCustom];
        [_<#name#> setTitle:<#buttonTitle#> forState:UIControlStateNormal];
'''

module_tableView = '''
        _<#name#>.delegate = self;
        _<#name#>.dataSource = self;
'''

module_collection = '''
        UICollectionViewFlowLayout *layout = [[UICollectionViewFlowLayout alloc] init];
        layout.itemSize = CGSizeMake(<#55#>, <#55#>);
        layout.minimumLineSpacing = <#15#>;
        layout.minimumInteritemSpacing = <#10#>;
        
        _<#name#> = [[UICollectionView alloc] initWithFrame:CGRectMake(0, 0, kScreenWidth, kScreenHeight) collectionViewLayout:layout];
        
        _<#name#>.backgroundColor = [Theme colorWhite];
        
        [_<#name#> registerClass:[<#PHMineCell#> class] forCellWithReuseIdentifier:<#@"PHMineCell"#>];
        
        _<#name#>.delegate = self;
        _<#name#>.dataSource = self;
'''

module_label = '''
        _<#name#>.textColor = <#color#>;
        _<#name#>.font = <#font#>;
        _<#name#>.numberOfLines = 0;
        _<#name#>.textAlignment = NSTextAlignmentCenter;
        _<#name#>.text = <#text#>;
'''

### 以上是模板

def highlightPrint(text):
    print('\033[33m{}\033[0m'.format(text))

def errorPrint(error):
    print('\033[31m{}\033[0m'.format(error))

# 处理参数
def makeParams(info):
    params = info.split(":")
    name = params[0]
    if len(params) <= 1:
        params.append('v')
        params.append('')
    if name == '':
        name = getClass(params[1])[2:]
        name = name[0].lower() + name[1:]
    if len(params) <= 2:
        params.append('d')
    return (name, params[1], params[2])


def getClass(key):
    return viewMap.get(key, key)

def getLayoutName(key):
    return layoutMap.get(key,key)

def getExtension(name, className):
    result = ''
    if className == 'UICollectionView':
        result = module_collection
    elif className == 'UIButton':
        result = module_button
    elif className == 'UITableView':
        result = module_tableView
    elif className == 'UILabel':
        result = module_label
    return result.replace('<#name#>', name)

def makeProperty(name, className):
    return "@property (nonatomic, strong){} *{};".format(className, name)

def makeGetFunc(name, className):
    extensionStr = getExtension(name, className)
    tempStr = getFunc
    if className == 'UICollectionView' or className == 'UIButton':
        tempStr = tempStr.replace('_<#name#> = [[<#type#> alloc] init];', '')
    return tempStr.replace('<#name#>', name).replace('<#type#>', className).replace('<#extension#>', extensionStr)

def makeMasonry(name, isVC, relation, last, padding):
    parentName = 'self.view' if isVC else 'self'
    result = ''
    if len(relation) == 1:
        if relation == 't':
            result = layoutT.replace('<#last#>', 'self.{}'.format(last))
        elif relation == 'l':
            result = layoutL.replace('<#last#>', 'self.{}'.format(last))
        elif relation == 'e':
            result = layoutEdge
        elif relation == 's':
            result = layoutSize
        elif relation == 'a':
            result = layoutAll
        elif relation == 'd':
            result = layoutDefault
    else: # 完全自定义布局
        params = relation.split('/')
        layoutLines = []
        for param in params:
            kvs = param.split(',')
            if len(kvs) != 2:
                continue
            ps = '.'
            hasOthre = False
            for k in kvs[0]:
                print('{}----{}'.format(k,kvs[1]))
                if k.isupper():
                    lower = k.lower()
                    other = layoutRela.get(lower,lower)
                    value = kvs[1] if kvs[1].isdigit() else '<#code#>'
                    layoutLines.append('    make.{}.equalTo(self.{}.mas_{}).offset({});'.format(getLayoutName(lower),last,other,value))
                else:
                    hasOthre = True
                    ps += getLayoutName(k) + '.'
            if hasOthre:
                if kvs[1].isdigit():
                    layoutLines.append('    make{}mas_equalTo({});'.format(ps,kvs[1]))
                else:
                    layoutLines.append('    make{}equalTo(self.{});'.format(ps,kvs[1]))
        result = layoutBase.replace('<#layout#>', '\n'.join(layoutLines))
    return result.replace('<#parent#>', parentName).replace('<#name#>', name).replace('<#padding#>', padding)

# 执行代码
def run(info):
    # 参数
    properties = []
    # get方法
    gets = []
    # 布局
    layouts = []
    
    params = info.split(' ')
    views = []

    # 分解参数和视图
    isVC = True
    padding = paddings
    for param in params:
        if param.startswith('-'):
            if param == '-view':
                isVC = False
            elif param.startswith('-p:'):
                padding = param.replace('-p:', '')
        else:
            if ':' in param:
                views.append(param)

    # 上一个视图名称
    lastName = ''
    for view in views:
         params = makeParams(view)
         name = params[0]
         className = getClass(params[1])
         layoutName = params[2]
         properties.append(makeProperty(name, className))
         gets.append(makeGetFunc(name, className))
         layouts.append(makeMasonry(name, isVC, layoutName, lastName, padding))
         lastName = name
    
    print('\n######################\n######## 🎉🎉🎉 ######\n######################\n')
    res = '#pragma mark - Property\n\n' + '\n'.join(properties) + '\n\n#pragma mark - Getter && Setter\n' + ''.join(gets) + '\n\n#pragma mark - Builder\n' + ''.join(layouts)
    highlightPrint(res)

if __name__ == "__main__":
    if len(sys.argv) <= 1:
        errorPrint('参数输入有误，请使用-help查看使用说明')
    elif '-help' in sys.argv:
        print(helpInfo)
    else:
        os.system('clear')
        run(' '.join(sys.argv[1:]))
