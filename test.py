# encoding=utf-8

import re, sys, time, chardet, paramiko, os, telnetlib
from multiprocessing import Process, Pool, Queue
import tkinter as tk
from tkinter import ttk


class Client(object):

    def __init__(self, thread_id, ip):
        self.thread_id = thread_id
        self.ip = ip

    def get_cmd(self, cmd_file_name, str):
        """从文件中读取命令放到对应的列表中"""
        all_tel_cmds = []
        all_ssh_cmds = []
        try:
            with open(cmd_file_name, "r") as fp:
                for line in fp:
                    if line.strip():
                        action, cmd = line.split("||")
                        if action == str and str == "telnet":
                            all_tel_cmds.append(cmd.strip("\n") + "\n")  # 确保每一条命令后面都带有换行符
                        elif action == str and str == "ssh":
                            all_ssh_cmds.append(cmd.strip("\n") + "\n")
                        else:
                            continue
        except IOError:
            with open(systemErr_path,"a+") as fp:
                fp.write("--"*15+"\n")
                fp.write("open %s fail!\n" % cmd_file_name)
        if str == "telnet":
            return all_tel_cmds
        else:
            return all_ssh_cmds

    def w_log(self, log_file_name, data):
        """将执行命令后的打印写入到log中"""
        if not os.path.exists(log_file_name):
            fp = open(log_file_name, "w")
            fp.write(data)
            fp.close()
        else:
            with open(log_file_name, "a+") as fp:
                fp.write(data)

    def prepare_create_folder(self):
        if os.path.exists(file_base + self.ip):
            pass
        else:
            os.makedirs(file_base + self.ip)

    def start_telnet_ssh(self):
        """Telnet远程登录：Windows客户端连接Linux服务器
        tn.read_until(expected, [timeout])：读取直到看到预期的字符串，或超时命中（默认为无超时）,可设置超时的时间；
                                       一般看到预期的字符串，会停顿，等到输入；
                                        这时候如果使用res = tn.read_until(expected, [timeout])获取到的数据为上次获取之后本次获取之前的所有输入输出

        tn.write(string)：写入字符串
        tn.read_very_eager()：方法获取的内容是上次获取之后本次获取之前的所有输入输出，如何判断为本次获取之前：一般是对端每次屏幕停止等待输入作为界限
                         比如说tn.write之前的数据为一次获取，然后执行命令之后回显又为一次获取，然后执行命令到出现---more---又为一次获取，
                        到下一个---more---又一次获取，每次获取的数据都是执行+回显出现等待输入作为一次获取，所以需要内次累加
        """

        if os.path.exists(file_base + self.ip + "\\cmd.txt"):
            # 连接Telnet服务器
            try:
                tn = telnetlib.Telnet(self.ip, 343, timeout=10)
            except TimeoutError:
                with open(systemErr_path, "a+") as fp:
                    fp.write("--" * 15 + "\n")
                    fp.write("telnet %s timeout!\n" % self.ip)

            # 等待[USERNAME]:出现后输入用户名
            tn.read_until(b"[USERNAME]:")
            tn.write(b"admin\n")

            # 等待[PASSWORD]:出现后输入密码
            tn.read_until(b"[PASSWORD]:")
            tn.write(b"admin\n")

            # 等待SCMIP2>>出现后输入名字执行
            tn.read_until(b"SCMIP2>>")
            data = ""
            all_cmds = self.get_cmd(file_base + self.ip + "\\cmd.txt", "telnet")
            for cmd in all_cmds:
                tn.write(cmd.encode())
                time.sleep(2)
                # 多屏显示的情况
                res = tn.read_until(b"--- More ---", 5)
                # print("*" * 20)
                # print(data)
                if res.endswith(b"--- More ---"):
                    data += res.decode().strip("--- More ---")
                    # print("*" * 20)
                    # print(data)
                    for i in range(5):
                        tn.write(b" ")
                        time.sleep(2)
                        # print("*"*20)
                        # print(data)
                        data += tn.read_very_eager().decode().strip("--- More ---")
                else:
                    data += res.decode()
            self.w_log(file_base + self.ip + "\\" + logdate + ".txt", data)
            tn.close()

            #ssh2连接

            try:
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(self.ip, 22, "admin", "admin")
            except TimeoutError:
                with open(systemErr_path, "a+") as fp:
                    fp.write("--" * 15 + "\n")
                    fp.write("ssh %s timeout!\n" % self.ip)
            all_cmds = self.get_cmd(file_base + self.ip + "\\cmd.txt", "ssh")
            self.w_log(file_base + self.ip + "\\" + logdate + ".txt", "\n" * 2 + "*" * 20 + "SSH" + "*" * 20 + "\n")
            for cmd in all_cmds:
                stdin, stdout, stderr = ssh.exec_command(cmd)
                time.sleep(0.3)
                res = stdout.read().decode("EUC-JP")
                # print(chardet.detect(res))
                self.w_log(file_base + self.ip + "\\" + logdate + ".txt", res)
            ssh.close()

        else:
            print("cmd.txt not exist!")


def thread_ip_port(path):
    """读取thread ID,IP,Port"""
    try:
        with open(path, "r") as fp:
            all_thread_ip_port_lists = []
            for line in fp:
                thread_ip_port_list = line.strip("\n").split(",")
                if re.match(r"\d", thread_ip_port_list[0]):
                    all_thread_ip_port_lists.append(thread_ip_port_list)
            return all_thread_ip_port_lists
    except IOError:
        with open(systemErr_path, "a+") as fp:
            fp.write("--" * 15 + "\n")
            fp.write("open %s fail!\n" % path)


if __name__ == "__main__":
    logdate = time.strftime("%Y-%m-%d-%H%M%S", time.localtime())
    basepath = os.getcwd()
    systemErr_path = basepath + "\\logs\\debug\\systemErr.log"
    file_base = basepath + "\\data\\"
    all_thread_ip_lists = thread_ip_port(file_base + "candidateNodes.csv")
    pool = Pool(processes=4)
    for thread_ip in all_thread_ip_lists:
        thread_id = thread_ip[0]
        ip = thread_ip[1]
        if thread_id == "1":
            thread1 = Client(thread_id, ip)
        elif thread_id == "2":
            thread2 = Client(thread_id, ip)
        elif thread_id == "3":
            thread3 = Client(thread_id, ip)
        else:
            thread4 = Client(thread_id, ip)

    window = tk.Tk(className="cmd Tool")
    window['padx'] = 5
    window['pady'] = 5

    # - - - - - - - - - - - - - - - - - - - - -
    # The thread1 frame

    thread1_frame = ttk.LabelFrame(window, text="Thread1", relief=tk.RIDGE)
    thread1_frame.grid(row=1, column=1, padx=5, pady=3, ipadx=3, ipady=3, sticky=tk.E + tk.W + tk.N + tk.S)

    entry_ip_label = ttk.Label(thread1_frame, text="IP:")
    entry_ip_label.grid(row=1, column=1, ipadx=3, sticky=tk.W)

    entry_ip = ttk.Entry(thread1_frame)
    try:
        entry_ip.insert(tk.END, thread1.ip)
    except NameError:
        pass
    entry_ip["state"] = "readonly"
    entry_ip.grid(row=1, column=2, columnspan=2, sticky=tk.W)

    try:
        button_prepare = ttk.Button(thread1_frame, text="Prepare",command=thread1.prepare_create_folder)
    except NameError:
        button_prepare = ttk.Button(thread1_frame, text="Prepare")
    button_prepare.grid(row=2, column=2, sticky=tk.W, pady=3)

    try:
        button_start = ttk.Button(thread1_frame, text="Start",command=thread1.start_telnet_ssh)
    except NameError:
        button_start = ttk.Button(thread1_frame, text="Start")
    button_start.grid(row=2, column=3, sticky=tk.W, pady=3)

    # - - - - - - - - - - - - - - - - - - - - -
    # The thread2 frame

    thread2_frame = ttk.LabelFrame(window, text="Thread2", relief=tk.RIDGE)
    thread2_frame.grid(row=1, column=4, padx=5, pady=3, ipadx=3, ipady=3, sticky=tk.E + tk.W + tk.N + tk.S)

    entry_ip_label = ttk.Label(thread2_frame, text="IP:")
    entry_ip_label.grid(row=1, column=4, ipadx=3, sticky=tk.W)

    entry_ip = ttk.Entry(thread2_frame)
    try:
        entry_ip.insert(tk.END, thread2.ip)
    except NameError:
        pass
    entry_ip["state"] = "readonly"
    entry_ip.grid(row=1, column=5, columnspan=2, sticky=tk.W)

    try:
        button_prepare = ttk.Button(thread2_frame, text="Prepare",command=thread2.prepare_create_folder)
    except NameError:
        button_prepare = ttk.Button(thread2_frame, text="Prepare")
    button_prepare.grid(row=2, column=5, sticky=tk.W, pady=3)

    try:
        button_start = ttk.Button(thread2_frame, text="Start",command=thread2.start_telnet_ssh)
    except NameError:
        button_start = ttk.Button(thread2_frame, text="Start")
    button_start.grid(row=2, column=6, sticky=tk.W, pady=3)

    # - - - - - - - - - - - - - - - - - - - - -
    # The thread3 frame
    thread3_frame = ttk.LabelFrame(window, text="Thread3", relief=tk.RIDGE)
    thread3_frame.grid(row=3, column=1, padx=5, pady=3, ipadx=3, ipady=3, sticky=tk.E + tk.W + tk.N + tk.S)

    entry_ip_label = ttk.Label(thread3_frame, text="IP:")
    entry_ip_label.grid(row=3, column=1, ipadx=3, sticky=tk.W)

    entry_ip = ttk.Entry(thread3_frame)
    try:
        entry_ip.insert(tk.END, thread3.ip)
    except NameError:
        pass
    entry_ip["state"] = "readonly"
    entry_ip.grid(row=3, column=2, columnspan=2, sticky=tk.W)

    try:
        button_prepare = ttk.Button(thread3_frame, text="Prepare",command=thread3.prepare_create_folder)
    except NameError:
        button_prepare = ttk.Button(thread3_frame, text="Prepare")
    button_prepare.grid(row=4, column=2, sticky=tk.W, pady=3)

    try:
        button_start = ttk.Button(thread3_frame, text="Start",command=thread3.start_telnet_ssh)
    except NameError:
        button_start = ttk.Button(thread3_frame, text="Start")
    button_start.grid(row=4, column=3, sticky=tk.W, pady=3)

    # - - - - - - - - - - - - - - - - - - - - -
    # The thread4 frame

    thread4_frame = ttk.LabelFrame(window, text="Thread4", relief=tk.RIDGE)
    thread4_frame.grid(row=3, column=4, padx=5, pady=3, ipadx=3, ipady=3, sticky=tk.E + tk.W + tk.N + tk.S)

    entry_ip_label = ttk.Label(thread4_frame, text="IP:")
    entry_ip_label.grid(row=3, column=4, ipadx=3, sticky=tk.W)

    entry_ip = ttk.Entry(thread4_frame)
    try:
        entry_ip.insert(tk.END, thread4.ip)
    except NameError:
        pass
    entry_ip["state"] = "readonly"
    entry_ip.grid(row=3, column=5, columnspan=2, sticky=tk.W)

    try:
        button_prepare = ttk.Button(thread4_frame, text="Prepare",command=thread4.prepare_create_folder)
    except NameError:
        button_prepare = ttk.Button(thread4_frame, text="Prepare")
    button_prepare.grid(row=4, column=5, sticky=tk.W, pady=3)

    try:
        button_start = ttk.Button(thread4_frame, text="Start",command=thread4.start_telnet_ssh)
    except NameError:
        button_start = ttk.Button(thread4_frame, text="Start")
    button_start.grid(row=4, column=6, sticky=tk.W, pady=3)

    window.mainloop()
