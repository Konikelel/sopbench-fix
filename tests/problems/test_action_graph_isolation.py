from env.helpers import dfsgather_ifg_func
from env.variables import domain_assistant_keys, domain_keys


def action_graph_nodes(domain, action):
    nodes, _, _ = dfsgather_ifg_func(domain_keys[domain](), domain_assistant_keys[domain], action, "full")
    return nodes


def test_action_graph_does_not_depend_on_previously_processed_domain():
    action_graph_nodes("bank", "get_account_balance")
    assert action_graph_nodes("library", "logout_user") == [
        ("logout_user", {"username": "username"}), "and",
        ("login_user", {"username": "username", "password": "password"}), "or",
        ("internal_check_username_exist", {"username": "username"}), ("internal_get_database", {})]
