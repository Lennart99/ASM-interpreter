from typing import List

import nodes


class ProgramContext:
    def __init__(self, text: List[nodes.Node], bss: List[nodes.Node], data: List[nodes.Node],
                 labels: List[nodes.Label], globalLabels: List[str]):
        self.text: List[nodes.Node] = text
        self.bss:  List[nodes.Node] = bss
        self.data: List[nodes.Node] = data
        self.labels: List[nodes.Label] = labels
        self.globalLabels: List[str] = globalLabels

    def __str__(self) -> str:
        return ".text: {} \n.bss: {} \n.data: {} \nLabels: {} \nGlobal labels: {}". \
            format(self.text, self.bss, self.data, self.labels, self.globalLabels)

    def __repr__(self) -> str:
        return self.__str__()
