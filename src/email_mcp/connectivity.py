"""
Email connectivity testing module.
Tests IMAP and SMTP server connections with provided credentials.
"""
import imaplib
import smtplib
import socket
from typing import Dict, Any


def test_imap_connection(
    server: str,
    port: int,
    username: str,
    password: str,
    timeout: int = 10
) -> Dict[str, str]:
    """
    Test IMAP server connection and authentication.

    Returns:
        dict with keys: status (success/failed), message, server, port
    """
    try:
        # Test basic TCP connection
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((server, port))
        sock.close()

        # Test IMAP connection and authentication
        client = imaplib.IMAP4_SSL(server, port)
        client.login(username, password)
        client.logout()

        return {
            "status": "success",
            "message": f"Successfully connected to {server}:{port}",
            "server": server,
            "port": port
        }
    except socket.timeout:
        return {
            "status": "failed",
            "message": f"Connection timeout to {server}:{port}",
            "server": server,
            "port": port
        }
    except socket.gaierror as e:
        return {
            "status": "failed",
            "message": f"DNS resolution failed for {server}: {str(e)}",
            "server": server,
            "port": port
        }
    except ConnectionRefusedError:
        return {
            "status": "failed",
            "message": f"Connection refused by {server}:{port}",
            "server": server,
            "port": port
        }
    except imaplib.IMAP4.error as e:
        return {
            "status": "failed",
            "message": f"IMAP authentication failed: {str(e)}",
            "server": server,
            "port": port
        }
    except Exception as e:
        return {
            "status": "failed",
            "message": f"IMAP connection error: {type(e).__name__}: {str(e)}",
            "server": server,
            "port": port
        }


def test_smtp_connection(
    server: str,
    port: int,
    username: str,
    password: str,
    timeout: int = 10
) -> Dict[str, str]:
    """
    Test SMTP server connection and authentication.

    Returns:
        dict with keys: status (success/failed), message, server, port
    """
    try:
        # Test basic TCP connection
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((server, port))
        sock.close()

        # Determine if SSL or STARTTLS based on port
        if port == 465 or port == 587:
            # Try SSL first
            try:
                client = smtplib.SMTP_SSL(server, port, timeout=timeout)
                client.login(username, password)
                client.quit()
                return {
                    "status": "success",
                    "message": f"Successfully connected via SSL to {server}:{port}",
                    "server": server,
                    "port": port
                }
            except Exception:
                # SSL failed, try with STARTTLS
                pass

        # Try STARTTLS
        client = smtplib.SMTP(server, port, timeout=timeout)
        client.ehlo()
        if client.has_extn("STARTTLS"):
            client.starttls()
            client.ehlo()
        client.login(username, password)
        client.quit()

        return {
            "status": "success",
            "message": f"Successfully connected via STARTTLS to {server}:{port}",
            "server": server,
            "port": port
        }
    except socket.timeout:
        return {
            "status": "failed",
            "message": f"Connection timeout to {server}:{port}",
            "server": server,
            "port": port
        }
    except socket.gaierror as e:
        return {
            "status": "failed",
            "message": f"DNS resolution failed for {server}: {str(e)}",
            "server": server,
            "port": port
        }
    except ConnectionRefusedError:
        return {
            "status": "failed",
            "message": f"Connection refused by {server}:{port}",
            "server": server,
            "port": port
        }
    except smtplib.SMTPAuthenticationError as e:
        return {
            "status": "failed",
            "message": f"SMTP authentication failed: {str(e)}",
            "server": server,
            "port": port
        }
    except smtplib.SMTPException as e:
        return {
            "status": "failed",
            "message": f"SMTP error: {str(e)}",
            "server": server,
            "port": port
        }
    except Exception as e:
        return {
            "status": "failed",
            "message": f"SMTP connection error: {type(e).__name__}: {str(e)}",
            "server": server,
            "port": port
        }


def test_email_connection(
    imap_server: str,
    imap_port: int,
    smtp_server: str,
    smtp_port: int,
    username: str,
    password: str,
    timeout: int = 10
) -> Dict[str, Any]:
    """
    Test both IMAP and SMTP connections.

    Returns:
        dict with keys: status (success/failed), message, imap_test, smtp_test
    """
    imap_result = test_imap_connection(imap_server, imap_port, username, password, timeout)
    smtp_result = test_smtp_connection(smtp_server, smtp_port, username, password, timeout)

    # Overall status
    if imap_result["status"] == "success" and smtp_result["status"] == "success":
        status = "success"
        message = "Both IMAP and SMTP connections successful"
    elif imap_result["status"] == "success" or smtp_result["status"] == "success":
        status = "partial"
        message = f"Partial success: IMAP={imap_result['status']}, SMTP={smtp_result['status']}"
    else:
        status = "failed"
        message = "Both IMAP and SMTP connections failed"

    return {
        "status": status,
        "message": message,
        "imap_test": imap_result,
        "smtp_test": smtp_result
    }
