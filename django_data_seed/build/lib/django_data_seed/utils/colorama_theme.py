from colorama import Fore, Style


class StdoutTextTheme:
    def stdout_success(self, message):
        print(Fore.GREEN + message + Style.RESET_ALL)

    def stdout_error(self, message):
        print(Fore.RED + message + Style.RESET_ALL)

    def stdout_warning(self, message):
        print(Fore.YELLOW + message + Style.RESET_ALL)

    def stdout_info(self, message):
        print(Fore.BLUE + message + Style.RESET_ALL)

    def stdout_standard(self, message):
        print(Fore.WHITE + message + Style.RESET_ALL)

    def stdout_headers(self, message):
        print(Fore.WHITE + Style.BRIGHT + message + Style.RESET_ALL)
