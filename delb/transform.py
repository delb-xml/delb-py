# Copyright (C) 2018-'22  Frank Sachsenheim
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
This module offers a canonical interface with the aim to make re-use of transforming
algorithms easier.

Let's look at it with examples::

   from delb.transform import Transformation


   class ResolveCopyOf(Transformation):
       def transform(self):
           for node in self.root.css_select("*[copyOf]"):
               source_id = node["copyOf"]
               source_node = self.origin_document.xpath(
                   f'//*[@xml:id="{source_id[1:]}"]'
               ).first
               cloned_node = source_node.clone(deep=True)
               cloned_node.id = None
               node.replace_with(cloned_node)


From such defined transformations instances can be called with a (sub-)tree and an
optional document where that tree originates from::

   resolve_copy_of = ResolveCopyOf()
   tree = resolve_copy_of(tree)  # where tree is an instance of TagNode


:class:`typing.NamedTuple` are used to define options for transformations::

   from typing import NamedTuple


   class ResolveChoiceOptions(NamedTuple):
       corr: bool = True
       reg: bool = True


   class ResolveChoice(Transformation):
       options_class = ResolveChoiceOptions

       def __init__(self, options):
           super().__init__(options)
           self.keep_selector = ",".join(
               (
                   "corr" if self.options.corr else "sic",
                   "reg" if self.options.reg else "orig"
               )
            )
           self.drop_selector = ",".join(
               (
                   "sic" if self.options.corr else "corr",
                   "orig" if self.options.reg else "reg"
               )
           )

       def transform(self):
           for choice_node in self.root.css_select("choice"):
               node_to_drop = choice_node.css_select(self.drop_selector).first
               node_to_drop.detach()

               node_to_keep = choice_node.css_select(self.keep_selector).first
               node_to_keep.detach(retain_child_nodes=True)

               choice_node.detach(retain_child_nodes=True)


A transformation class that defines an ``option_class`` property can then either be used
with its defaults or with alternate options::

   resolve_choice = ResolveChoice()
   tree = resolve_choice(tree)

   resolve_choice = ResolveChoice(ResolveChoiceOptions(reg=False))
   tree = resolve_choice(tree)


Finally, concrete transformations can be chained, both as classes or instances. The
interface allows also to chain multiple chains::

   from delb.transform import TransformationSequence

   tidy_up = TransformationSequence(ResolveCopyOf, resolve_choice)
   tree = tidy_up(tree)


.. attention::
   This is an experimental feature. It might change significantly in the future or be
   removed altogether.
"""

from abc import ABC, abstractmethod
from typing import NamedTuple, Optional, Type, Union

from delb import Document, TagNode


#


class TransformationBase(ABC):
    """This base class defines the calling interface of transformations."""

    @abstractmethod
    def __call__(self, root: TagNode, document: Document = None) -> TagNode:
        pass


class Transformation(TransformationBase):
    """This is a base class for any transformation algorithm."""

    options_class: Optional[Type] = None

    def __init__(self, options: Optional[NamedTuple] = None):
        self.root: Optional[TagNode] = None
        self.document: Optional[Document] = None
        if options is None and self.options_class is not None:
            options = self.options_class()

        self.options = options

    def __call__(self, root: TagNode, document: Document = None) -> TagNode:
        if root.document is None:
            # TODO clarify why a copy is needed for trees that aren't part of a
            #      document
            root = Document(root).root
        self.root = root
        self.origin_document = document
        self.transform()
        result = self.root
        self.root = self.document = None
        return result

    @abstractmethod
    def transform(self):
        """
        This method needs to implement the transformation logic. When it is called,
        the instance has two attributes assigned from its call:

        ``root`` is the node that the transformation was called to transform with.
        ``origin_document`` is the document that was possibly passed as second argument.
        """
        pass


class TransformationSequence(TransformationBase):
    """
    A transformation sequence can be used to combine any number of both
    :class:`Transformation` (provided as class or instantiated with options) and other
    :class:`TransformationSequence` instances or classes.
    """

    def __init__(
        self,
        *transformations: Union[TransformationBase, Type[TransformationBase]],
    ):
        self.transformations = []
        for transformation in transformations:
            if isinstance(transformation, type) and issubclass(
                transformation, TransformationBase
            ):
                self.transformations.append(transformation())
            elif isinstance(transformation, TransformationBase):
                self.transformations.append(transformation)
            else:
                raise TypeError(
                    "Only subclasses of TransformationBase or instances of such are "
                    "allowed."
                )

    def __call__(self, root: TagNode, document: Document = None) -> TagNode:
        for transformation in self.transformations:
            root = transformation(root, document=document)
        return root
