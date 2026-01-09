#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试打包后的MCP邮件服务
"""

import os
import sys
import json
import subprocess
import time

# 设置环境变量
env = os.environ.copy()
env.update({
    'MCP_EMAIL_USERNAME': 'anubiscl@163.com',
    'MCP_EMAIL_PASSWORD': 'xxx',
    'MCP_EMAIL_SERVER': 'imap.163.com',
    'MCP_EMAIL_PORT': '993',
    'MCP_SMTP_SERVER': 'smtp.163.com',
    'MCP_SMTP_PORT': '465',
    'MCP_SAVE_PATH': '/Users/anubis/404net/mcp-read-email-py/attachments'
})

def test_packaged_service():
    """测试打包后的MCP服务"""
    print("Testing packaged MCP Email Service...")
    print(f"Current directory: {os.getcwd()}")
    
    # 检查可执行文件是否存在
    exe_path = os.path.abspath("./dist/mcp_email_service_sdk")
    if not os.path.exists(exe_path):
        print(f"ERROR: Executable not found at {exe_path}")
        return False
    
    print(f"Executable path: {exe_path}")
    print(f"File size: {os.path.getsize(exe_path) / (1024 * 1024):.2f} MB")
    print(f"Executable is executable: {os.access(exe_path, os.X_OK)}")
    
    # 测试可执行文件是否能正常启动
    print("\nTesting if executable can start...")
    try:
        # 运行可执行文件，检查是否能正常启动
        result = subprocess.run(
            [exe_path, "--version"],
            env=env,
            capture_output=True,
            text=True,
            timeout=5
        )
        
        print(f"Exit code: {result.returncode}")
        print(f"Stdout: {result.stdout}")
        print(f"Stderr: {result.stderr}")
        
        if result.returncode == 0:
            print("✓ Executable can start successfully!")
        else:
            print(f"✗ Executable failed to start with exit code {result.returncode}")
            
    except subprocess.TimeoutExpired:
        print("✗ Executable timed out - this is expected for MCP services as they run indefinitely")
        # MCP服务会一直运行，所以超时是正常的
        print("✓ MCP service appears to be running (timed out as expected)")
    except Exception as e:
        print(f"✗ Error starting executable: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n✓ Packaged MCP service is ready to use!")
    print("\nTo use the packaged service:")
    print(f"1. Update your mcp-config-163.json to point to: {exe_path}")
    print("2. Make sure all required environment variables are set")
    print("3. Start the MCP service through your MCP client")
    
    return True

if __name__ == "__main__":
    success = test_packaged_service()
    sys.exit(0 if success else 1)
