# ossFileList

存储桶遍历漏洞利用脚本
批量提取未授权的存储桶OSS的文件路径、大小、后缀名称
提取的结果会自动生成到csv和xlsx文件中

安装：
`pip3 install pandas`

使用：
`python3 ossFileList.py -u https://xxx.oss-cn-xxx.aliyuncs.com/`
![use](.\assets\use.png)

TODO:

下个版本增加url批量 `python3 ossFileList.py -f filename`



1. 自动生成的csv文件后，通过filetype拆分成不同的工作表，易读。

![lizi](.\assets\lizi.png)

![通过filetype分成不同工作表](.\assets\通过filetype分成不同工作表.png)

2. 修复XML解析有误，无法遍历的bug
![XML解析有误](.\assets\XML解析有误.png)


免责声明
本工具只作为学术交流，禁止使用工具做违法的事情
----------------------------

![image](https://github.com/source-xu/oss-x/assets/56073532/592ff801-d27a-4fba-b664-91537c8312c4)

![image](https://github.com/source-xu/oss-x/assets/56073532/54dffeb3-5590-44da-9834-de261d912bb3)
原作者：https://github.com/source-xu/ossx