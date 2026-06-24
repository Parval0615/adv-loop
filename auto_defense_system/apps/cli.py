import warnings
warnings.filterwarnings("ignore")
import os
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
from auto_defense_system.agent.graph import graph_invoke, clear_history
from auto_defense_system.security.permission import ROLE_PERMISSIONS, get_role_info, DEFAULT_ROLE
from auto_defense_system.security.audit import read_audit_log

if __name__ == "__main__":
    print("="*70)
    print("AI Security Agent | 企业级终版 | 全链路安全防护")
    print(f"当前角色：{get_role_info(DEFAULT_ROLE)['name']} | {get_role_info(DEFAULT_ROLE)['desc']}")
    print("q退出 | clear清空记忆 | role切换角色 | log查看审计日志")
    print("="*70)

    current_role = DEFAULT_ROLE
    current_user_id = "cli_user"

    while True:
        user_input = input("\n请输入问题：").strip()
        # 退出指令
        if user_input.lower() == "q":
            print("程序已退出，感谢使用！")
            break
        # 清空记忆
        if user_input.lower() == "clear":
            clear_history(current_user_id)
            print("[OK] 对话记忆已清空（SQLite 持久化状态已重置）")
            continue
        # 切换角色
        if user_input.lower() == "role":
            print("\n可选角色列表：")
            for role_key, role_info in ROLE_PERMISSIONS.items():
                print(f"- {role_key}：{role_info['name']} | {role_info['desc']}")
            new_role = input("请输入角色代码：").strip().lower()
            if new_role in ROLE_PERMISSIONS:
                current_role = new_role
                clear_history(current_user_id)
                print(f"[OK] 已切换为【{ROLE_PERMISSIONS[current_role]['name']}】，记忆已清空")
            else:
                print("[X] 无效角色代码")
            continue
        # 查看审计日志
        if user_input.lower() == "log":
            line_count = input("请输入要查看的日志条数（默认20）：").strip()
            line_count = int(line_count) if line_count.isdigit() else 20
            print("\n【最新审计日志】")
            print(read_audit_log(line_count))
            continue
        # 空输入跳过
        if not user_input:
            print("请输入有效问题")
            continue

        # 调用Agent（不传 chat_history，纯 checkpointer 模式）
        try:
            answer = graph_invoke(
                user_input=user_input,
                role=current_role,
                user_id=current_user_id,
            )
            print("\n【Agent回答】：", answer)
        except Exception as e:
            print("\n【系统错误】：", str(e))