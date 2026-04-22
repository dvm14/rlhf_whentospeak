# 🎙️ VoiceIQ — Preference Lab

A Streamlit-based interactive labeling interface for collecting human preferences on voice assistant behavior, specifically training the model to understand **when to speak and when to listen**.

## Overview

VoiceIQ Preference Lab is an RLHF (Reinforcement Learning from Human Feedback) data collection tool designed to help improve voice assistants by gathering preference annotations from human labelers. Each scenario presents two alternative voice assistant responses—one where the assistant speaks and one where it remains silent—and labelers choose which is more appropriate.

## Features

- 🗣️ **Preference Collection**: Choose between "Assistant Speaks" or "Assistant Silent" for realistic conversation scenarios
- 👥 **Multi-Labeler Support**: Track contributions from multiple labelers with inter-rater reliability tracking
- 📊 **Smart Queue Management**: Prioritizes unlabeled scenarios globally, then those labeled by others (for diversity)
- 💾 **Database Persistence**: Stores all annotations in PostgreSQL with full audit trails
- 📥 **Data Export**: Download results in JSONL or CSV format
- 🎨 **Beautiful UI**: Custom dark-mode interface with real-time progress tracking
- ⏭️ **Skip Option**: Allows labelers to skip ambiguous scenarios

## Setup

### Prerequisites

- Python 3.8+
- PostgreSQL database
- Streamlit

### Installation

1. Clone the repository:
```bash
git clone https://github.com/dvm14/rlhf_whentospeak.git
cd rlhf_whentospeak
