/* $Id: QIRichTextLabel.cpp $ */
/** @file
 * VBox Qt GUI - VirtualBox Qt extensions: QIRichTextLabel class implementation.
 */

/*
 * Copyright (C) 2012-2017 Oracle Corporation
 *
 * This file is part of VirtualBox Open Source Edition (OSE), as
 * available from http://www.virtualbox.org. This file is free software;
 * you can redistribute it and/or modify it under the terms of the GNU
 * General Public License (GPL) as published by the Free Software
 * Foundation, in version 2 as it comes in the "COPYING" file of the
 * VirtualBox OSE distribution. VirtualBox OSE is distributed in the
 * hope that it will be useful, but WITHOUT ANY WARRANTY of any kind.
 */

#ifdef VBOX_WITH_PRECOMPILED_HEADERS
# include <precomp.h>
#else  /* !VBOX_WITH_PRECOMPILED_HEADERS */

/* Global includes: */
# include <QtMath>
# include <QUrl>
# include <QVBoxLayout>

/* Local includes: */
# include "QIRichTextLabel.h"

#endif /* !VBOX_WITH_PRECOMPILED_HEADERS */


/* Constructor: */
QIRichTextLabel::QIRichTextLabel(QWidget *pParent)
    : QWidget(pParent)
    , m_pTextEdit(new QTextEdit(this))
    , m_iMinimumTextWidth(0)
{
    /* Setup self: */
    setSizePolicy(QSizePolicy::MinimumExpanding, QSizePolicy::Fixed);

    /* Setup text-edit: */
    m_pTextEdit->setReadOnly(true);
    m_pTextEdit->setFocusPolicy(Qt::NoFocus);
    m_pTextEdit->setFrameShape(QFrame::NoFrame);
    m_pTextEdit->setVerticalScrollBarPolicy(Qt::ScrollBarAlwaysOff);
    m_pTextEdit->setSizePolicy(QSizePolicy::Ignored, QSizePolicy::Ignored);

    /* Tune text-edit viewport palette: */
    m_pTextEdit->viewport()->setAutoFillBackground(false);
    QPalette pal = m_pTextEdit->viewport()->palette();
    pal.setColor(QPalette::Active,   QPalette::Text, pal.color(QPalette::Active,   QPalette::WindowText));
    pal.setColor(QPalette::Inactive, QPalette::Text, pal.color(QPalette::Inactive, QPalette::WindowText));
    pal.setColor(QPalette::Disabled, QPalette::Text, pal.color(QPalette::Disabled, QPalette::WindowText));
    m_pTextEdit->viewport()->setPalette(pal);

    /* Add into parent: */
    QVBoxLayout *pMainLayout = new QVBoxLayout(this);
    pMainLayout->setMargin(0);
    pMainLayout->addWidget(m_pTextEdit);
}

/* Text getter: */
QString QIRichTextLabel::text() const
{
    return m_pTextEdit->toHtml();
}

/* Register image: */
void QIRichTextLabel::registerImage(const QImage &image, const QString &strName)
{
    /* Register passed image in internal text-document: */
    m_pTextEdit->document()->addResource(QTextDocument::ImageResource, QUrl(strName), QVariant(image));
}

/* Word-wrap mode getter: */
QTextOption::WrapMode QIRichTextLabel::wordWrapMode() const
{
    return m_pTextEdit->wordWrapMode();
}

/* Word-wrap mode setter: */
void QIRichTextLabel::setWordWrapMode(QTextOption::WrapMode policy)
{
    m_pTextEdit->setWordWrapMode(policy);
}

/* API: Event-filter setter: */
void QIRichTextLabel::installEventFilter(QObject *pFilterObj)
{
    QWidget::installEventFilter(pFilterObj);
    m_pTextEdit->installEventFilter(pFilterObj);
}

/* Minimum text-width setter: */
void QIRichTextLabel::setMinimumTextWidth(int iMinimumTextWidth)
{
    /* Remember minimum text width: */
    m_iMinimumTextWidth = iMinimumTextWidth;

    /* Get corresponding QTextDocument: */
    QTextDocument *pTextDocument = m_pTextEdit->document();
    /* Bug in QTextDocument (?) : setTextWidth doesn't work from the first time. */
    for (int iTry = 0; pTextDocument->textWidth() != m_iMinimumTextWidth && iTry < 3; ++iTry)
        pTextDocument->setTextWidth(m_iMinimumTextWidth);
    /* Get corresponding QTextDocument size: */
    QSize size = pTextDocument->size().toSize();

    /* Resize to content size: */
    m_pTextEdit->setMinimumSize(size);
    layout()->activate();
}

/* Text setter: */
void QIRichTextLabel::setText(const QString &strText)
{
    /* Set text: */
    m_pTextEdit->setHtml(strText);

    /* Get corresponding QTextDocument: */
    QTextDocument *pTextDocument = m_pTextEdit->document();

    // WORKAROUND:
    // Ok, here is the trick.  In Qt 5.6.x initial QTextDocument size is always 0x0
    // even if contents present.  To make QTextDocument calculate initial size we
    // need to pass it some initial text-width, that way size should be calualated
    // on the basis of passed width.  No idea why but in Qt 5.6.x first calculated
    // size doesn't actually linked to initially passed text-width, somehow it
    // always have 640px width and various height which depends on currently set
    // contents.  So, we just using 640px as initial text-width.
    pTextDocument->setTextWidth(640);

    /* Now get that initial size which is 640xY, and propose new text-width as 4/3
     * of hypothetical width current content would have laid out as square: */
    const QSize oldSize = pTextDocument->size().toSize();
    const int iProposedWidth = qSqrt(oldSize.width() * oldSize.height()) * 4 / 3;
    pTextDocument->setTextWidth(iProposedWidth);

    /* Get effective QTextDocument size: */
    const QSize newSize = pTextDocument->size().toSize();

    /* Set minimum text width to corresponding value: */
    setMinimumTextWidth(m_iMinimumTextWidth == 0 ? newSize.width() : m_iMinimumTextWidth);
}

