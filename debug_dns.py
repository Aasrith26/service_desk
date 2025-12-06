import socket

h1 = "shyam-mhvudwae-eastus2.services.ai.azure.com"
h2 = "shyam-mhvudwae-eastus2.openai.azure.com"

try:
    socket.gethostbyname(h1)
    print("HOST1_OK")
except:
    print("HOST1_FAIL")

try:
    socket.gethostbyname(h2)
    print("HOST2_OK")
except:
    print("HOST2_FAIL")
